"""Tests for schedule export domain models."""

import pytest
from pydantic import ValidationError

from regulahub.sisreg.models import EnrichedExportRow, ExportFilters, ScheduleExportResponse, ScheduleExportRow


class TestExportFilters:
    def test_valid_filters(self):
        f = ExportFilters(date_from="19/03/2026", date_to="31/03/2026", usernames=["op1"])
        assert f.date_from == "19/03/2026"
        assert f.date_to == "31/03/2026"
        assert f.cpf == "0"
        assert f.procedimento == ""
        assert f.file_type == 1
        assert f.profile_type == "SOLICITANTE"

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError, match="dd/MM/yyyy"):
            ExportFilters(date_from="2026-03-19", date_to="31/03/2026", usernames=["op1"])

    def test_invalid_date_to(self):
        with pytest.raises(ValidationError):
            ExportFilters(date_from="19/03/2026", date_to="2026-03-31", usernames=["op1"])

    def test_empty_usernames_rejected(self):
        with pytest.raises(ValidationError):
            ExportFilters(date_from="19/03/2026", date_to="31/03/2026", usernames=[])

    def test_custom_filters(self):
        f = ExportFilters(
            date_from="01/01/2026",
            date_to="31/01/2026",
            cpf="12345678901",
            procedimento="0301010307",
            file_type=0,
            profile_type="EXECUTANTE",
            usernames=["op1", "op2"],
        )
        assert f.cpf == "12345678901"
        assert f.procedimento == "0301010307"
        assert f.file_type == 0
        assert f.profile_type == "EXECUTANTE"
        assert len(f.usernames) == 2


class TestScheduleExportRow:
    def test_defaults_all_empty(self):
        row = ScheduleExportRow()
        assert row.solicitacao == ""
        assert row.nome_profissional_solicitante == ""
        assert row.cpf_proficional_executante == ""  # typo preserved

    def test_all_38_fields(self):
        fields = ScheduleExportRow.model_fields
        assert len(fields) == 38

    def test_from_dict(self):
        row = ScheduleExportRow(
            solicitacao="453274466",
            descricao_procedimento="TELECONSULTA EM UROLOGIA GERAL",
            cns="898006209973606",
            nome="INACIO FIALHO DE SOUZA ROCHA",
            situacao="PENDENTE",
        )
        assert row.solicitacao == "453274466"
        assert row.descricao_procedimento == "TELECONSULTA EM UROLOGIA GERAL"
        assert row.situacao == "PENDENTE"


class TestScheduleExportResponse:
    def test_construction(self):
        resp = ScheduleExportResponse(
            items=[ScheduleExportRow(solicitacao="1")],
            total=1,
            operators_queried=2,
            operators_succeeded=1,
        )
        assert resp.total == 1
        assert resp.operators_queried == 2
        assert resp.operators_succeeded == 1
        assert len(resp.items) == 1


class TestEnrichedExportRow:
    def test_inherits_schedule_fields(self):
        row = EnrichedExportRow(
            solicitacao="123",
            nome="Test",
            cpf_paciente="12345678901",
            raca="Parda",
        )
        assert row.solicitacao == "123"
        assert row.cpf_paciente == "12345678901"
        assert row.raca == "Parda"
        assert row.email_paciente is None

    def test_has_extra_fields(self):
        extra = {"cpf_paciente", "email_paciente", "telefone_cadsus", "nome_pai", "raca", "cns_definitivo"}
        enriched_fields = set(EnrichedExportRow.model_fields.keys())
        base_fields = set(ScheduleExportRow.model_fields.keys())
        assert extra == enriched_fields - base_fields
