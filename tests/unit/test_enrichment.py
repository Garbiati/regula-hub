"""Tests for CADSUS enrichment in schedule export service."""

from unittest.mock import MagicMock, patch

import pytest

from regulahub.integrations.cadsus_client import CadsusPatientData
from regulahub.services.schedule_export_service import enrich_rows_with_cadsus
from regulahub.sisreg.models import ScheduleExportRow


def _row(solicitacao: str, cns: str = "", procedimento: str = "CONSULTA") -> ScheduleExportRow:
    return ScheduleExportRow(
        solicitacao=solicitacao,
        cns=cns,
        descricao_procedimento=procedimento,
    )


def _patient(cpf: str = "12345678901", **kwargs) -> CadsusPatientData:
    return CadsusPatientData(cpf=cpf, **kwargs)


def _mock_settings(enabled: bool = True):
    settings = MagicMock()
    settings.cadsus_enabled = enabled
    return settings


class TestEnrichRowsWithCadsus:
    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_enrichment_fills_cpf(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = _patient(cpf="99988877766")

        rows = [_row("A1", cns="111222333444555")]
        result = await enrich_rows_with_cadsus(rows)

        assert len(result) == 1
        assert result[0].cpf_paciente == "99988877766"
        assert result[0].solicitacao == "A1"

    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_procedure_filter_case_insensitive(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = _patient()

        rows = [
            _row("A1", cns="111", procedimento="TELECONSULTA EM UROLOGIA"),
            _row("A2", cns="222", procedimento="CONSULTA EM FONOAUDIOLOGIA"),
        ]
        result = await enrich_rows_with_cadsus(rows, procedure_filter="teleconsulta")

        assert len(result) == 1
        assert result[0].solicitacao == "A1"

    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_duplicate_cns_single_lookup(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = _patient()

        # Two rows with same CNS
        rows = [
            _row("A1", cns="SAME_CNS"),
            _row("A2", cns="SAME_CNS"),
        ]
        result = await enrich_rows_with_cadsus(rows)

        assert len(result) == 2
        # Only one CADSUS call for the same CNS
        assert mock_get_patient.call_count == 1

    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_cadsus_failure_keeps_csv_data(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = None

        rows = [_row("A1", cns="111222333444555")]
        result = await enrich_rows_with_cadsus(rows)

        assert len(result) == 1
        assert result[0].cpf_paciente is None
        assert result[0].solicitacao == "A1"

    @pytest.mark.asyncio
    @patch("regulahub.config.get_cadsus_settings")
    async def test_cadsus_disabled_returns_unenriched(self, mock_get_settings):
        mock_get_settings.return_value = _mock_settings(enabled=False)

        rows = [_row("A1", cns="111")]
        result = await enrich_rows_with_cadsus(rows)

        assert len(result) == 1
        assert result[0].cpf_paciente is None

    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_no_filter_enriches_all(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = _patient()

        rows = [
            _row("A1", cns="111", procedimento="TELECONSULTA"),
            _row("A2", cns="222", procedimento="FONOAUDIOLOGIA"),
        ]
        result = await enrich_rows_with_cadsus(rows, procedure_filter=None)

        assert len(result) == 2

    @pytest.mark.asyncio
    @patch("regulahub.integrations.cadsus_client.CadsusClient.get_patient_by_cns")
    @patch("regulahub.config.get_cadsus_settings")
    async def test_enrichment_includes_all_cadsus_fields(self, mock_get_settings, mock_get_patient):
        mock_get_settings.return_value = _mock_settings()
        mock_get_patient.return_value = _patient(
            cpf="11122233344",
            email="test@test.com",
            phone="92999990000",
            father_name="JOSE",
            race="03",
            cns="898006209973606",
        )

        rows = [_row("A1", cns="111")]
        result = await enrich_rows_with_cadsus(rows)

        r = result[0]
        assert r.cpf_paciente == "11122233344"
        assert r.email_paciente == "test@test.com"
        assert r.telefone_cadsus == "92999990000"
        assert r.nome_pai == "JOSE"
        assert r.raca == "03"
        assert r.cns_definitivo == "898006209973606"
