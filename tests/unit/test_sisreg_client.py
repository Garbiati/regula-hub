"""Tests for SisReg HTTP client."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from regulahub.sisreg.client import SisregClient, SisregLoginError
from regulahub.sisreg.models import SearchFilters

FIXTURES = Path(__file__).parent.parent / "fixtures"
BASE_URL = "https://sisregiii.saude.gov.br"

# Minimal HTML that simulates a successful login response with menu elements
LOGIN_SUCCESS_HTML = """
<html><body>
<ul>
<li><a href="/page1">Item 1</a></li>
<li><a href="/page2">Item 2</a></li>
<li><a href="/cgi-bin/gerenciador_solicitacao">Agendamentos</a></li>
<li><a href="/page4">Item 4</a></li>
<li><a href="/page5">Item 5</a>
  <ul>
    <li><a href="/sub1">Sub 1</a></li>
    <li><a href="/cgi-bin/gerenciador_solicitacao">Solicitante</a></li>
  </ul>
</li>
</ul>
</body></html>
"""

LOGIN_EXPIRED_HTML = """
<html><body>
<table><tbody>
<tr><td><center><i><span>Sua sessão expirou</span></i></center></td></tr>
</tbody></table>
</body></html>
"""


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


@respx.mock
@pytest.mark.asyncio
async def test_login_success():
    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    # Mock the profile menu navigation (Videofonista menu href)
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "testuser", "testpass") as client:
        assert client is not None


@respx.mock
@pytest.mark.asyncio
async def test_login_failure_on_expired_session():
    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_EXPIRED_HTML))

    with pytest.raises(SisregLoginError):
        async with SisregClient(BASE_URL, "testuser", "testpass"):
            pass


@respx.mock
@pytest.mark.asyncio
async def test_search_returns_items():
    listing_html = _read_fixture("sisreg_listing.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(return_value=httpx.Response(200, text=listing_html))
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        filters = SearchFilters(
            date_from="15/03/2026",
            date_to="15/03/2026",
            profile_type="VIDEOFONISTA",
            usernames=["user"],
        )
        result = await client.search(filters)
        assert result.total == 2
        assert result.items[0].code == "12345"


@respx.mock
@pytest.mark.asyncio
async def test_detail_returns_fields():
    detail_html = _read_fixture("sisreg_detail.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(return_value=httpx.Response(200, text=detail_html))
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        detail = await client.detail("12345")
        assert detail.req_unit_name == "UBS CENTRO - RJ"
        assert detail.procedure_name == "TELECONSULTA EM CARDIOLOGIA"


@respx.mock
@pytest.mark.asyncio
async def test_search_sends_all_cgi_params():
    """Verify that all filter fields are mapped to the correct CGI query params."""
    listing_html = _read_fixture("sisreg_listing.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    search_route = respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text=listing_html)
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        filters = SearchFilters(
            date_from="15/03/2026",
            date_to="16/03/2026",
            search_type="solicitacao",
            situation="1",
            items_per_page="50",
            sol_code="99999",
            patient_cns="123456789012345",
            patient_name="JOAO SILVA",
            cnes_solicitation="1234567",
            cnes_execute="7654321",
            procedure_unified_code="0301010030",
            procedure_internal_code="123",
            procedure_description="TELECONSULTA",
            profile_type="VIDEOFONISTA",
            usernames=["user"],
        )
        await client.search(filters)

    assert search_route.called
    # Skip first call (menu navigation) and check the search call
    search_request = search_route.calls.last.request
    qs = parse_qs(urlparse(str(search_request.url)).query)

    assert qs["etapa"] == ["LISTAR_SOLICITACOES"]
    assert qs["tipo_periodo"] == ["S"]
    assert qs["dt_inicial"] == ["15/03/2026"]
    assert qs["dt_final"] == ["16/03/2026"]
    assert qs["cmb_situacao"] == ["1"]
    assert qs["qtd_itens_pag"] == ["50"]
    assert qs["co_solicitacao"] == ["99999"]
    assert qs["cns_paciente"] == ["123456789012345"]
    assert qs["no_usuario"] == ["JOAO SILVA"]
    assert qs["cnes_solicitante"] == ["1234567"]
    assert qs["cnes_executante"] == ["7654321"]
    assert qs["co_proc_unificado"] == ["0301010030"]
    assert qs["co_pa_interno"] == ["123"]
    assert qs["ds_procedimento"] == ["TELECONSULTA"]
    assert qs["ordenacao"] == ["2"]
    assert qs["pagina"] == ["0"]


@respx.mock
@pytest.mark.asyncio
async def test_search_omits_optional_params_when_none():
    """Verify that None optional fields are not sent as CGI params."""
    listing_html = _read_fixture("sisreg_listing.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    search_route = respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text=listing_html)
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        filters = SearchFilters(
            date_from="15/03/2026",
            date_to="15/03/2026",
            profile_type="VIDEOFONISTA",
            usernames=["user"],
        )
        await client.search(filters)

    search_request = search_route.calls.last.request
    qs = parse_qs(urlparse(str(search_request.url)).query)

    # Required params are present with correct SisReg names
    assert qs["etapa"] == ["LISTAR_SOLICITACOES"]
    assert qs["tipo_periodo"] == ["A"]
    assert qs["dt_inicial"] == ["15/03/2026"]
    assert qs["cmb_situacao"] == ["9"]
    assert qs["qtd_itens_pag"] == ["0"]

    # Optional params are absent
    assert "co_solicitacao" not in qs
    assert "cns_paciente" not in qs
    assert "no_usuario" not in qs
    assert "cnes_solicitante" not in qs
    assert "cnes_executante" not in qs
    assert "co_proc_unificado" not in qs
    assert "co_pa_interno" not in qs
    assert "ds_procedimento" not in qs


# ─── CadWeb lookup ────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_cadweb_lookup_success():
    """CadWeb lookup returns CadwebPatientData with CPF and phone."""
    cadweb_html = _read_fixture("cadweb_result.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/cadweb50").mock(return_value=httpx.Response(200, text=cadweb_html))
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        result = await client.cadweb_lookup("700508134911455")

    assert result is not None
    assert result.cpf == "33525528272"
    assert result.mother_name == "FRANCISCA JUVENCIO DA COSTA"
    assert result.phone_ddd == "92"
    assert result.phone_number == "99211-9712"


@respx.mock
@pytest.mark.asyncio
async def test_cadweb_lookup_no_result():
    """CadWeb response without 'DADOS PESSOAIS' → None."""
    no_result_html = "<html><body><p>Nenhum registro encontrado</p></body></html>"

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/cadweb50").mock(return_value=httpx.Response(200, text=no_result_html))
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        result = await client.cadweb_lookup("999999999999999")

    assert result is None


@respx.mock
@pytest.mark.asyncio
async def test_cadweb_lookup_session_expired():
    """CadWeb with expired session → SessionExpiredError → retry."""
    cadweb_html = _read_fixture("cadweb_result.html")

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    # First call returns expired, second returns valid data
    cadweb_route = respx.get(f"{BASE_URL}/cgi-bin/cadweb50")
    cadweb_route.side_effect = [
        httpx.Response(200, text=LOGIN_EXPIRED_HTML),
        httpx.Response(200, text=cadweb_html),
    ]
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass") as client:
        result = await client.cadweb_lookup("700508134911455")

    assert result is not None
    assert result.cpf == "33525528272"


# ─── Schedule export ──────────────────────────────────────────────────────


EXPORT_FIXTURE_PATH = FIXTURES / "export_schedule.csv"

# Simulates the export form page with a hidden `unidade` field
EXPORT_FORM_HTML = """
<html><body>
<form method="POST" action="/cgi-bin/expo_solicitacoes">
<input type="hidden" name="unidade" value="2018756">
Data inicial: <input name="data1">
Data final: <input name="data2">
<input type="submit" value="Exportar">
</form>
</body></html>
"""


@respx.mock
@pytest.mark.asyncio
async def test_export_schedule_success():
    """export_schedule GETs the form (hidden unidade), then POSTs with it."""
    csv_bytes = EXPORT_FIXTURE_PATH.read_bytes()

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(return_value=httpx.Response(200, text=EXPORT_FORM_HTML))
    export_route = respx.post(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(
        return_value=httpx.Response(200, content=csv_bytes)
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass", "SOLICITANTE") as client:
        result = await client.export_schedule("19/03/2026", "31/03/2026")

    assert result == csv_bytes
    assert export_route.called

    # Verify form data includes hidden unidade field
    req = export_route.calls.last.request
    body = req.content.decode()
    assert "etapa=exportar" in body
    assert "tp_arquivo=1" in body
    assert "unidade=2018756" in body


@respx.mock
@pytest.mark.asyncio
async def test_export_schedule_custom_filters():
    """export_schedule sends custom CPF and procedimento."""
    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(return_value=httpx.Response(200, text=EXPORT_FORM_HTML))
    export_route = respx.post(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(
        return_value=httpx.Response(200, content=b"header\r\n")
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass", "SOLICITANTE") as client:
        await client.export_schedule(
            "01/01/2026",
            "31/01/2026",
            cpf="12345678901",
            procedimento="0301010307",
            file_type=0,
        )

    req = export_route.calls.last.request
    body = req.content.decode()
    assert "cpf=12345678901" in body
    assert "tp_arquivo=0" in body
    assert "unidade=2018756" in body


@respx.mock
@pytest.mark.asyncio
async def test_export_schedule_session_expired_retry():
    """export_schedule retries on session expiry (including form reload)."""
    csv_bytes = b"solicitacao;col2\r\n123;val\r\n"

    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(return_value=httpx.Response(200, text=EXPORT_FORM_HTML))
    export_route = respx.post(f"{BASE_URL}/cgi-bin/expo_solicitacoes")
    export_route.side_effect = [
        httpx.Response(200, content=LOGIN_EXPIRED_HTML.encode()),
        httpx.Response(200, content=csv_bytes),
    ]
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass", "SOLICITANTE") as client:
        result = await client.export_schedule("19/03/2026", "31/03/2026")

    assert result == csv_bytes
    assert export_route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_export_schedule_defaults():
    """export_schedule uses defaults: cpf='0', procedimento='', tp_arquivo='1'."""
    respx.post(f"{BASE_URL}/").mock(return_value=httpx.Response(200, text=LOGIN_SUCCESS_HTML))
    respx.get(f"{BASE_URL}/cgi-bin/gerenciador_solicitacao").mock(
        return_value=httpx.Response(200, text="<html><body>OK</body></html>")
    )
    respx.get(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(return_value=httpx.Response(200, text=EXPORT_FORM_HTML))
    export_route = respx.post(f"{BASE_URL}/cgi-bin/expo_solicitacoes").mock(
        return_value=httpx.Response(200, content=b"header\r\n")
    )
    respx.get(f"{BASE_URL}/cgi-bin/sair").mock(return_value=httpx.Response(200, text="OK"))

    async with SisregClient(BASE_URL, "user", "pass", "SOLICITANTE") as client:
        await client.export_schedule("19/03/2026", "31/03/2026")

    req = export_route.calls.last.request
    body = req.content.decode()
    assert "cpf=0" in body
    assert "tp_arquivo=1" in body
    assert "unidade=2018756" in body
