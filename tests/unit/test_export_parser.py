"""Tests for SisReg schedule export CSV parser."""

from pathlib import Path

from regulahub.sisreg.export_parser import EXPECTED_COLUMN_COUNT, EXPORT_COLUMNS, parse_export_csv

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "export_schedule.csv"


class TestExportColumns:
    def test_column_count(self):
        assert EXPECTED_COLUMN_COUNT == 38

    def test_first_column(self):
        assert EXPORT_COLUMNS[0] == "solicitacao"

    def test_last_column(self):
        assert EXPORT_COLUMNS[-1] == "nome_profissional_solicitante"

    def test_typo_preserved(self):
        assert "cpf_proficional_executante" in EXPORT_COLUMNS


class TestParseExportCsv:
    def test_parse_fixture(self):
        raw = FIXTURE_PATH.read_bytes()
        rows = parse_export_csv(raw)
        assert len(rows) == 3

    def test_first_row_fields(self):
        raw = FIXTURE_PATH.read_bytes()
        rows = parse_export_csv(raw)
        row = rows[0]
        assert row.solicitacao == "100000001"
        assert row.codigo_interno == "0739212"
        assert row.codigo_unificado == "0301010307"
        assert row.descricao_procedimento == "TELECONSULTA EM UROLOGIA GERAL"
        assert row.cpf_proficional_executante == "11111111111"
        assert row.nome_profissional_executante == "JOAO SILVA SANTOS"
        assert row.data_agendamento == "23.03.2026"
        assert row.hr_agendamento == "12:00"
        assert row.tipo == "0"
        assert row.cns == "111222333444555"
        assert row.nome == "MARIA OLIVEIRA COSTA"
        assert row.dt_nascimento == "24.07.2020"
        assert row.idade == "05"
        assert row.idade_meses == "67"
        assert row.nome_mae == "ANA OLIVEIRA COSTA"
        assert row.tipo_logradouro == "RUA"
        assert row.logradouro == "DAS FLORES"
        assert row.complemento == ""
        assert row.numero_logradouro == "170"
        assert row.bairro == "CENTRO"
        assert row.cep == "69000100"
        assert row.telefone == "(92)99100-0001"
        assert row.municipio == "MANAUS"
        assert row.ibge == "130260"
        assert row.mun_solicitante == "MANAUS"
        assert row.ibge_solicitante == "130260"
        assert row.cnes_solicitante == "2013002"
        assert row.unidade_fantasia == "USF TESTE ALPHA"
        assert row.sexo == "M"
        assert row.data_solicitacao == "05.01.2023"
        assert row.operador_solicitante == "11111111111-CARLOS"
        assert row.data_autorizacao == "13.03.2026"
        assert row.operador_autorizador == "PATRICIA-22222222222"
        assert row.valor_procedimento == "10.00"
        assert row.situacao == "PENDENTE"
        assert row.cid == "Q628"
        assert row.cpf_profissional_solicitante == "33333333333"
        assert row.nome_profissional_solicitante == "FERNANDA SOUZA LIMA"

    def test_empty_csv_header_only(self):
        header = ";".join(EXPORT_COLUMNS) + "\r\n"
        rows = parse_export_csv(header.encode("utf-8"))
        assert rows == []

    def test_empty_bytes(self):
        rows = parse_export_csv(b"")
        assert rows == []

    def test_malformed_rows_skipped(self):
        header = ";".join(EXPORT_COLUMNS) + "\n"
        good = ";".join(["val"] * 38) + "\n"
        bad = "only;two;columns\n"
        raw = (header + good + bad).encode("utf-8")
        rows = parse_export_csv(raw)
        assert len(rows) == 1

    def test_whitespace_stripped(self):
        header = ";".join(EXPORT_COLUMNS) + "\n"
        values = [" val "] * 38
        row_line = ";".join(values) + "\n"
        raw = (header + row_line).encode("utf-8")
        rows = parse_export_csv(raw)
        assert rows[0].solicitacao == "val"
        assert rows[0].nome_profissional_solicitante == "val"

    def test_utf8_accented_characters(self):
        header = ";".join(EXPORT_COLUMNS) + "\n"
        values = [""] * 38
        values[0] = "12345"
        values[10] = "JOSÉ AÇAÍ DA SILVA"
        values[14] = "MARIA CONCEIÇÃO"
        row_line = ";".join(values) + "\n"
        raw = (header + row_line).encode("utf-8")
        rows = parse_export_csv(raw)
        assert rows[0].nome == "JOSÉ AÇAÍ DA SILVA"
        assert rows[0].nome_mae == "MARIA CONCEIÇÃO"

    def test_solicitacao_is_dedup_key(self):
        """solicitacao (first column) serves as deduplication key in the service layer."""
        raw = FIXTURE_PATH.read_bytes()
        rows = parse_export_csv(raw)
        codes = [r.solicitacao for r in rows]
        assert len(codes) == len(set(codes))

    def test_female_patient(self):
        raw = FIXTURE_PATH.read_bytes()
        rows = parse_export_csv(raw)
        row = rows[2]
        assert row.sexo == "F"
        assert row.nome == "JULIA GONCALVES SILVA"

    def test_empty_cpf_solicitante(self):
        """Third row has empty cpf_profissional_solicitante."""
        raw = FIXTURE_PATH.read_bytes()
        rows = parse_export_csv(raw)
        assert rows[2].cpf_profissional_solicitante == ""
