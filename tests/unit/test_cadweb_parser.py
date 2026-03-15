"""Tests for CadWeb (Consulta CNS) HTML parser."""

from pathlib import Path

import pytest

from regulahub.sisreg.parser import _clean_cpf, _extract_cadweb_phone, _find_labeled_value, parse_cadweb

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture
def cadweb_html() -> str:
    return _read_fixture("cadweb_result.html")


class TestParseCadwebFull:
    def test_parse_all_fields(self, cadweb_html):
        """Full CadWeb parse extracts CPF, mother_name, father_name, sex, phone."""
        result = parse_cadweb(cadweb_html)

        assert result.cpf == "33525528272"
        assert result.mother_name == "FRANCISCA JUVENCIO DA COSTA"
        assert result.father_name == "JOSE JUVENCIO CORDEIRO"
        assert result.sex == "MASCULINO"
        assert result.phone_type == "CELULAR"
        assert result.phone_ddd == "92"
        assert result.phone_number == "99211-9712"

    def test_cpf_cleaned(self, cadweb_html):
        """CPF '335.255.282-72' is cleaned to '33525528272'."""
        result = parse_cadweb(cadweb_html)
        assert result.cpf == "33525528272"
        assert len(result.cpf) == 11
        assert result.cpf.isdigit()


class TestParseCadwebNoPhone:
    def test_no_phone_table(self):
        """CadWeb page without phone table → phone fields are None."""
        html = """<html><body>
        <table>
        <tr><td colspan="4" class="tit_lista"><b>DADOS PESSOAIS:</b></td></tr>
        <tr><td><b>Nome da Mãe:</b></td><td>MARIA DA SILVA</td></tr>
        <tr><td colspan="4" class="tit_lista"><b>DOCUMENTOS:</b></td></tr>
        <tr><td><b>CPF:</b></td></tr>
        <tr><td>123.456.789-09</td></tr>
        </table>
        </body></html>"""

        result = parse_cadweb(html)
        assert result.phone_type is None
        assert result.phone_ddd is None
        assert result.phone_number is None
        assert result.cpf == "12345678909"
        assert result.mother_name == "MARIA DA SILVA"


class TestParseCadwebCelularPreferred:
    def test_celular_over_residencial(self):
        """Multiple phones → CELULAR is preferred."""
        html = """<html><body>
        <table>
        <tr><td colspan="4" class="tit_lista"><b>DADOS PESSOAIS:</b></td></tr>
        </table>
        <table>
        <tr><th>Tipo Telefone</th><th>DDD</th><th>Número</th></tr>
        <tr><td>RESIDENCIAL</td><td>(92)</td><td>3333-4444</td></tr>
        <tr><td>CELULAR</td><td>(92)</td><td>98765-4321</td></tr>
        </table>
        </body></html>"""

        result = parse_cadweb(html)
        assert result.phone_type == "CELULAR"
        assert result.phone_ddd == "92"
        assert result.phone_number == "98765-4321"

    def test_single_residencial(self):
        """Only RESIDENCIAL phone → uses it as fallback."""
        html = """<html><body>
        <table>
        <tr><td colspan="4" class="tit_lista"><b>DADOS PESSOAIS:</b></td></tr>
        </table>
        <table>
        <tr><th>Tipo Telefone</th><th>DDD</th><th>Número</th></tr>
        <tr><td>RESIDENCIAL</td><td>(11)</td><td>3333-4444</td></tr>
        </table>
        </body></html>"""

        result = parse_cadweb(html)
        assert result.phone_type == "RESIDENCIAL"
        assert result.phone_ddd == "11"
        assert result.phone_number == "3333-4444"


class TestFindLabeledValue:
    def test_same_row_pattern(self):
        """Label and value in same row, adjacent <td>s."""
        from selectolax.parser import HTMLParser

        html = "<html><body><table><tr><td><b>Nome da Mãe:</b></td><td>MARIA SILVA</td></tr></table></body></html>"
        tree = HTMLParser(html)
        assert _find_labeled_value(tree, "Nome da Mãe:") == "MARIA SILVA"

    def test_next_row_pattern(self):
        """Label in one row, value in next row."""
        from selectolax.parser import HTMLParser

        html = """<html><body><table>
        <tr><td><b>CPF:</b></td></tr>
        <tr><td>123.456.789-09</td></tr>
        </table></body></html>"""
        tree = HTMLParser(html)
        assert _find_labeled_value(tree, "CPF:") == "123.456.789-09"

    def test_label_not_found(self):
        """Missing label → None."""
        from selectolax.parser import HTMLParser

        html = "<html><body><table><tr><td><b>Nome:</b></td><td>JOAO</td></tr></table></body></html>"
        tree = HTMLParser(html)
        assert _find_labeled_value(tree, "CPF:") is None

    def test_value_is_dash(self):
        """Value '---' is treated as missing → None."""
        from selectolax.parser import HTMLParser

        html = "<html><body><table><tr><td><b>Nome Social / Apelido:</b></td><td>---</td></tr></table></body></html>"
        tree = HTMLParser(html)
        assert _find_labeled_value(tree, "Nome Social / Apelido:") is None


class TestCleanCpf:
    def test_formatted_cpf(self):
        assert _clean_cpf("335.255.282-72") == "33525528272"

    def test_already_clean(self):
        assert _clean_cpf("33525528272") == "33525528272"

    def test_none(self):
        assert _clean_cpf(None) is None

    def test_empty(self):
        assert _clean_cpf("") is None

    def test_invalid_length(self):
        assert _clean_cpf("123") is None

    def test_non_digit(self):
        assert _clean_cpf("abcdefghijk") is None

    def test_whitespace(self):
        assert _clean_cpf("  335.255.282-72  ") == "33525528272"


class TestExtractCadwebPhone:
    def test_no_phone_table(self):
        from selectolax.parser import HTMLParser

        html = "<html><body><table><tr><td>No phones here</td></tr></table></body></html>"
        tree = HTMLParser(html)
        assert _extract_cadweb_phone(tree) == (None, None, None)
