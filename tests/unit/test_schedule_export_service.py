"""Tests for schedule export service."""

from unittest.mock import MagicMock, patch

import pytest

from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.services.schedule_export_service import (
    build_csv_bytes,
    build_txt_bytes,
    export_schedules,
)
from regulahub.sisreg.export_parser import EXPORT_COLUMNS
from regulahub.sisreg.models import ExportFilters, ScheduleExportRow


def _make_row(solicitacao: str, **kwargs: str) -> ScheduleExportRow:
    return ScheduleExportRow(solicitacao=solicitacao, **kwargs)


class TestBuildCsvBytes:
    def test_csv_header_and_rows(self):
        rows = [_make_row("100", descricao_procedimento="CONSULTA", nome="JOAO")]
        result = build_csv_bytes(rows)
        lines = result.decode("utf-8").splitlines()
        assert lines[0] == ";".join(EXPORT_COLUMNS)
        assert lines[1].startswith("100;")

    def test_csv_semicolon_separator(self):
        rows = [_make_row("200")]
        result = build_csv_bytes(rows)
        header_line = result.decode("utf-8").splitlines()[0]
        assert ";" in header_line
        assert "\t" not in header_line

    def test_csv_empty_rows(self):
        result = build_csv_bytes([])
        lines = result.decode("utf-8").strip().splitlines()
        assert len(lines) == 1  # header only

    def test_csv_utf8_encoding(self):
        rows = [_make_row("300", nome="JOSÉ AÇAÍ")]
        result = build_csv_bytes(rows)
        assert "JOSÉ AÇAÍ" in result.decode("utf-8")


class TestBuildTxtBytes:
    def test_txt_tab_separator(self):
        rows = [_make_row("100")]
        result = build_txt_bytes(rows)
        header_line = result.decode("utf-8").splitlines()[0]
        assert "\t" in header_line
        assert ";" not in header_line


class TestExportSchedules:
    @pytest.mark.asyncio
    @patch("regulahub.services.schedule_export_service._export_single_operator")
    @patch("regulahub.services.schedule_export_service._resolve_solicitante_credentials")
    async def test_two_operators_with_dedup(self, mock_resolve, mock_export):
        mock_resolve.return_value = [("op1", "pw1"), ("op2", "pw2")]
        # Both operators return overlapping rows
        mock_export.side_effect = [
            [_make_row("A1", nome="Patient 1"), _make_row("A2", nome="Patient 2")],
            [_make_row("A2", nome="Patient 2 dup"), _make_row("A3", nome="Patient 3")],
        ]

        filters = ExportFilters(date_from="19/03/2026", date_to="31/03/2026", usernames=["op1", "op2"])
        result = await export_schedules(filters, MagicMock())

        assert result.total == 3  # A1, A2, A3 (A2 deduped)
        assert result.operators_queried == 2
        assert result.operators_succeeded == 2
        codes = [r.solicitacao for r in result.items]
        assert codes == ["A1", "A2", "A3"]
        # First-seen wins: A2 should have "Patient 2", not "Patient 2 dup"
        assert result.items[1].nome == "Patient 2"

    @pytest.mark.asyncio
    @patch("regulahub.services.schedule_export_service._export_single_operator")
    @patch("regulahub.services.schedule_export_service._resolve_solicitante_credentials")
    async def test_one_operator_fails_partial_results(self, mock_resolve, mock_export):
        mock_resolve.return_value = [("op1", "pw1"), ("op2", "pw2")]
        mock_export.side_effect = [
            [_make_row("A1")],
            [],  # op2 failed, returned empty
        ]

        filters = ExportFilters(date_from="19/03/2026", date_to="31/03/2026", usernames=["op1", "op2"])
        result = await export_schedules(filters, MagicMock())

        assert result.total == 1
        assert result.operators_succeeded == 1

    @pytest.mark.asyncio
    @patch("regulahub.services.schedule_export_service._resolve_solicitante_credentials")
    async def test_no_credentials_raises(self, mock_resolve):
        mock_resolve.side_effect = CredentialNotFoundError("No credentials")

        filters = ExportFilters(date_from="19/03/2026", date_to="31/03/2026", usernames=["op1"])
        with pytest.raises(CredentialNotFoundError):
            await export_schedules(filters, MagicMock())
