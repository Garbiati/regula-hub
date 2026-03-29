"""Tests for SisReg HTML parser."""

from pathlib import Path

from regulahub.sisreg.parser import extract_phone, parse_detail, parse_listing

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


class TestParseListing:
    def test_parses_two_rows(self):
        html = _read_fixture("sisreg_listing.html")
        items = parse_listing(html)
        assert len(items) == 2

    def test_first_row_fields(self):
        html = _read_fixture("sisreg_listing.html")
        items = parse_listing(html)
        row = items[0]
        assert row.code == "12345"
        assert row.request_date == "15/03/2026"
        assert row.risk == 2
        assert row.patient_name == "MARIA SILVA"
        assert row.age == "45"
        assert row.procedure == "TELECONSULTA EM CARDIOLOGIA"
        assert row.cid == "I10"
        assert row.dept_solicitation == "UBS CENTRO"
        assert row.dept_execute == "HOSPITAL REGIONAL"
        assert row.status == "AGE/PEN/EXEC"

    def test_second_row_code(self):
        html = _read_fixture("sisreg_listing.html")
        items = parse_listing(html)
        assert items[1].code == "67890"
        assert items[1].risk == 0

    def test_empty_html_returns_empty_list(self):
        items = parse_listing("<html><body></body></html>")
        assert items == []

    def test_skips_header_rows(self):
        html = """
        <table class="table_listagem">
        <tbody>
        <tr><td>Header</td><td>H2</td><td>H3</td><td>H4</td><td>H5</td>
        <td>H6</td><td>H7</td><td>H8</td><td>H9</td><td>H10</td>
        <td>H11</td><td>H12</td><td>H13</td></tr>
        </tbody>
        </table>
        """
        items = parse_listing(html)
        assert items == []


class TestParseDetail:
    def test_parses_confirmation_key(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.confirmation_key == "CONF-ABC-123"

    def test_parses_requesting_unit(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.req_unit_name == "UBS CENTRO - RJ"
        assert detail.req_unit_cnes == "1234567"
        assert detail.solicitation_operator == "OPERADOR SOL 01"
        assert detail.videocall_operator == "OPERADOR VIDEO 01"

    def test_parses_executing_unit(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.exec_unit_name == "POLICLINICA CODAJAS"
        assert detail.exec_unit_cnes == "7654321"
        assert detail.exec_unit_authorizer == "AUTORIZADOR 01"
        assert detail.exec_unit_address == "AV CODAJAS"
        assert detail.exec_unit_address_number == "26"
        assert detail.exec_unit_address_complement == "SALA 2"
        assert detail.exec_unit_cep == "69065-130"
        assert detail.exec_unit_neighborhood == "CACHOEIRINHA"
        assert detail.exec_unit_municipality == "MANAUS"
        assert detail.exec_unit_professional == "DR. CARLOS OLIVEIRA"

    def test_parses_patient(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.patient_cns == "898001234567890"
        assert detail.patient_name == "MARIA SILVA"
        assert detail.patient_birth_date == "15/06/1980 (45 anos)"

    def test_parses_solicitation(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.sol_code == "12345"
        assert detail.sol_status == "AGE/PEN/EXEC"
        assert detail.sol_cid == "I10"
        assert detail.sol_risk == "VERDE- Nao Urgente"
        assert detail.sol_doctor_cpf == "123.456.789-00"
        assert detail.sol_doctor_crm == "CRM-RJ 54321"
        assert detail.sol_doctor_name == "DR. CARLOS OLIVEIRA"
        assert detail.sol_regulatory_center == "CENTRAL ESTADUAL RJ"

    def test_parses_procedure(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.procedure_name == "TELECONSULTA EM CARDIOLOGIA"
        assert detail.procedure_code == "0301010072"

    def test_parses_justification(self):
        html = _read_fixture("sisreg_detail.html")
        detail = parse_detail(html)
        assert detail.justification == "Paciente hipertenso, acompanhamento regular"


class TestExtractPhone:
    def test_extracts_mobile_from_fixture(self):
        html = _read_fixture("sisreg_detail.html")
        phone = extract_phone(html)
        assert phone is not None
        assert phone.ddd == "21"
        assert phone.number == "99876-5432"
        assert phone.phone_type == "mobile"

    def test_extracts_mobile_phone(self):
        # Phone at tbody 4, row 16 (DETAIL_PHONE_PRIMARY position)
        html = """
        <div id="fichaAmbulatorial"><table>
        <tbody></tbody><tbody></tbody><tbody></tbody>
        <tbody>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td>(21) 99876-5432</td></tr>
        </tbody>
        </table></div>
        """
        phone = extract_phone(html)
        assert phone is not None
        assert phone.ddd == "21"
        assert phone.number == "99876-5432"
        assert phone.phone_type == "mobile"

    def test_cleans_exibir_lista_text(self):
        # Phone at tbody 4, row 14 (DETAIL_PHONE_FALLBACK position)
        html = """
        <div id="fichaAmbulatorial"><table>
        <tbody></tbody><tbody></tbody><tbody></tbody>
        <tbody>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr><tr><td></td></tr><tr><td></td></tr><tr><td></td></tr>
        <tr><td></td></tr>
        <tr><td>(11) 3456-7890 (Exibir Lista Detalhada)</td></tr>
        </tbody>
        </table></div>
        """
        phone = extract_phone(html)
        assert phone is not None
        assert phone.ddd == "11"
        assert phone.number == "3456-7890"
        assert phone.phone_type == "landline"

    def test_returns_none_for_no_phone(self):
        html = "<div id='fichaAmbulatorial'></div>"
        phone = extract_phone(html)
        assert phone is None
