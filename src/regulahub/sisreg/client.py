"""SisReg HTTP client — login, search, detail."""

import logging

import httpx
from selectolax.parser import HTMLParser
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from regulahub.sisreg.models import AppointmentDetail, CadwebPatientData, SearchFilters, SearchResponse
from regulahub.sisreg.parser import parse_cadweb, parse_detail, parse_listing
from regulahub.sisreg.selectors import (
    CADWEB_CGI_PATH,
    EXPORT_CGI_PATH,
    MENU_HREF_EXPORT,
    MENU_HREF_SEARCH,
    SEARCH_CGI_PATH,
    SESSION_EXPIRED_SELECTOR,
    SESSION_EXPIRED_TEXT,
)
from regulahub.utils.crypto import hash_password
from regulahub.utils.masking import mask_username

logger = logging.getLogger(__name__)


class SessionExpiredError(Exception):
    """SisReg session has expired and needs re-authentication."""


class SisregLoginError(Exception):
    """Login to SisReg failed."""


class SisregClient:
    """Async HTTP client for SisReg III."""

    # Map frontend search type names to SisReg CGI single-letter codes
    _SEARCH_TYPE_MAP: dict[str, str] = {
        "solicitacao": "S",
        "agendamento": "A",
        "execucao": "E",
        "confirmacao": "P",
        "cancelamento": "C",
    }

    def __init__(self, base_url: str, username: str, password: str, profile_type: str = "VIDEOFONISTA") -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._profile_type = profile_type.upper()
        self._user_hash = mask_username(username)
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "SisregClient":
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            follow_redirects=True,
            timeout=httpx.Timeout(30.0),
        )
        await self._login()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http:
            import contextlib

            with contextlib.suppress(Exception):
                await self._http.get("/cgi-bin/sair")
            await self._http.aclose()
            self._http = None

    async def _login(self) -> None:
        """Authenticate to SisReg using SHA-256 hashed password."""
        hashed = hash_password(self._password)
        data = {
            "usuario": self._username,
            "senha_256": hashed,
            "etapa": "ACESSO",
        }
        resp = await self._http.post("/", data=data)
        resp.raise_for_status()

        if self._is_session_expired(resp.text):
            raise SisregLoginError(f"Login failed for user {self._user_hash}")

        # Verify we got a valid session by checking for menu links (href-based, position-independent)
        tree = HTMLParser(resp.text)
        menu_links = self._extract_menu_hrefs(tree)
        if not menu_links:
            raise SisregLoginError(f"Login response has no menu for user {self._user_hash}")

        # Navigate to the search page to establish session context.
        # SisReg requires navigating through the menu to bind the unit to the session.
        nav_href = menu_links.get("search") or menu_links.get("export")
        if nav_href:
            nav_resp = await self._http.get(nav_href)
            nav_resp.raise_for_status()
            logger.info("SisReg session context set for user %s via %s", self._user_hash, nav_href)
        else:
            logger.warning("No search/export menu link found for user %s", self._user_hash)

        logger.info("SisReg login successful for user %s", self._user_hash)

    def _is_session_expired(self, html: str) -> bool:
        """Check if the response indicates an expired session."""
        tree = HTMLParser(html)
        node = tree.css_first(SESSION_EXPIRED_SELECTOR)
        return bool(node and SESSION_EXPIRED_TEXT in (node.text(strip=True) or "").lower())

    def _check_session(self, html: str) -> None:
        """Raise SessionExpiredError if session has expired."""
        if self._is_session_expired(html):
            logger.warning("Session expired for user %s", self._user_hash)
            raise SessionExpiredError(f"Session expired for user {self._user_hash}")

    @staticmethod
    def _extract_menu_hrefs(tree: HTMLParser) -> dict[str, str]:
        """Extract known feature hrefs from the SisReg menu by matching href attributes.

        Returns a dict with keys like "search", "export" mapped to their href paths.
        This is position-independent — works regardless of menu item order or profile.
        """
        result: dict[str, str] = {}
        for node in tree.css("a[href]"):
            href = node.attributes.get("href", "")
            if MENU_HREF_SEARCH in href:
                result["search"] = href
            elif MENU_HREF_EXPORT in href:
                result["export"] = href
        return result

    @retry(
        retry=retry_if_exception_type(SessionExpiredError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def search(self, filters: SearchFilters) -> SearchResponse:
        """Search SisReg appointments using full CGI parameters."""
        search_type_code = self._SEARCH_TYPE_MAP.get(filters.search_type, filters.search_type)

        params: dict[str, str] = {
            "etapa": "LISTAR_SOLICITACOES",
            "tipo_periodo": search_type_code,
            "dt_inicial": filters.date_from,
            "dt_final": filters.date_to,
            "cmb_situacao": filters.situation,
            "qtd_itens_pag": filters.items_per_page,
            "ordenacao": "2",
            "pagina": "0",
        }
        if filters.sol_code:
            params["co_solicitacao"] = filters.sol_code
        if filters.patient_cns:
            params["cns_paciente"] = filters.patient_cns
        if filters.patient_name:
            params["no_usuario"] = filters.patient_name
        if filters.cnes_solicitation:
            params["cnes_solicitante"] = filters.cnes_solicitation
        if filters.cnes_execute:
            params["cnes_executante"] = filters.cnes_execute
        if filters.procedure_unified_code:
            params["co_proc_unificado"] = filters.procedure_unified_code
        if filters.procedure_internal_code:
            params["co_pa_interno"] = filters.procedure_internal_code
        if filters.procedure_description:
            params["ds_procedimento"] = filters.procedure_description

        resp = await self._http.get(SEARCH_CGI_PATH, params=params)
        resp.raise_for_status()
        self._check_session(resp.text)

        items = parse_listing(resp.text)
        logger.info("SisReg search returned %d items for user %s", len(items), self._user_hash)
        return SearchResponse(items=items, total=len(items))

    @retry(
        retry=retry_if_exception_type(SessionExpiredError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def cadweb_lookup(self, cns: str) -> CadwebPatientData | None:
        """Query CadWeb (Consulta CNS) for patient demographics by CNS.

        Returns None if no patient found for the given CNS.
        """
        params = {
            "metodo": "pesquisar",
            "cpf_cns": cns,
            "standalone": "1",
        }
        resp = await self._http.get(CADWEB_CGI_PATH, params=params)
        resp.raise_for_status()
        self._check_session(resp.text)

        if "DADOS PESSOAIS" not in resp.text:
            logger.info("CadWeb: no patient found for CNS (user %s)", self._user_hash)
            return None

        result = parse_cadweb(resp.text)
        logger.info("CadWeb: patient found for CNS (user %s)", self._user_hash)
        return result

    @retry(
        retry=retry_if_exception_type(SessionExpiredError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def detail(self, code: str) -> AppointmentDetail:
        """Get appointment detail by solicitation code."""
        params = {
            "etapa": "VISUALIZAR_FICHA",
            "co_seq_solicitacao": code,
        }
        resp = await self._http.get(SEARCH_CGI_PATH, params=params)
        resp.raise_for_status()
        self._check_session(resp.text)

        result = parse_detail(resp.text)
        logger.info("SisReg detail fetched for code %s by user %s", code, self._user_hash)
        return result

    async def _load_export_form(self) -> dict[str, str]:
        """GET the export page to capture hidden form fields (especially `unidade`).

        SisReg populates the `unidade` hidden field from the session when the form page loads.
        We must include it in the POST for the export to return data for the correct unit.
        """
        resp = await self._http.get(EXPORT_CGI_PATH)
        resp.raise_for_status()
        self._check_session(resp.text)

        tree = HTMLParser(resp.text)
        hidden_fields: dict[str, str] = {}
        for inp in tree.css("input[type='hidden']"):
            name = inp.attributes.get("name", "")
            value = inp.attributes.get("value", "")
            if name:
                hidden_fields[name] = value

        if "unidade" in hidden_fields:
            logger.info("Export form loaded, unidade=%s for user %s", hidden_fields["unidade"], self._user_hash)
        else:
            logger.warning("Export form has no 'unidade' hidden field for user %s", self._user_hash)

        return hidden_fields

    @retry(
        retry=retry_if_exception_type(SessionExpiredError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def export_schedule(
        self,
        date_from: str,
        date_to: str,
        *,
        cpf: str = "0",
        procedimento: str = "",
        file_type: int = 1,
    ) -> bytes:
        """Export schedule data via SisReg CSV/TXT endpoint.

        Flow: GET the export form first to capture hidden fields (unidade),
        then POST with all form data including the hidden fields.

        Args:
            date_from: Start date (dd/MM/yyyy).
            date_to: End date (dd/MM/yyyy).
            cpf: Professional CPF filter ("0" for all).
            procedimento: Procedure code filter (empty for all).
            file_type: 0=TXT (tab), 1=CSV (semicolon).

        Returns:
            Raw bytes of the exported file.
        """
        # Load the export form to capture hidden fields (unidade, etc.)
        hidden_fields = await self._load_export_form()

        data = {
            **hidden_fields,
            "data1": date_from,
            "data2": date_to,
            "cpf": cpf,
            "procedimento": procedimento,
            "tp_arquivo": str(file_type),
            "etapa": "exportar",
        }
        resp = await self._http.post(EXPORT_CGI_PATH, data=data)
        resp.raise_for_status()

        # Check for session expiry in the response text
        text = resp.content.decode("utf-8", errors="replace")
        self._check_session(text)

        # Detect HTML responses — SisReg returns HTML error pages when session context is wrong
        content_type = resp.headers.get("content-type", "")
        stripped = text.strip()
        if stripped.lower().startswith(("<!doctype", "<html")) or "text/html" in content_type.lower():
            logger.warning(
                "SisReg export returned HTML instead of CSV for user %s (content-type: %s, first 200 chars: %s)",
                self._user_hash,
                content_type,
                stripped[:200],
            )
            raise SessionExpiredError(f"Export returned HTML instead of CSV for user {self._user_hash}")

        content_len = len(resp.content)
        if content_len < 1000:
            logger.warning(
                "SisReg export response suspiciously small for user %s (%d bytes): %r",
                self._user_hash,
                content_len,
                text[:500],
            )
        else:
            logger.info("SisReg schedule export completed for user %s (%d bytes)", self._user_hash, content_len)
        return resp.content
