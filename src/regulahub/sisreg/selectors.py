"""CSS selectors for SisReg HTML parsing."""

# ── Login ──────────────────────────────────────────────────────────────────────
LOGIN_URL_PATH = "/"
LOGIN_FORM_FIELDS = {"etapa": "ACESSO"}

# Session expiry detection — substring match on text content
SESSION_EXPIRED_SELECTOR = "body > table td center i span"
SESSION_EXPIRED_TEXT = "expirou"

# ── Menu navigation (href-based, independent of menu item position) ───────────
# After login, the SisReg response contains a <ul class="sf-menu"> with navigation links.
# We match links by their `href` attribute to avoid breakage when menu order changes.
#
# Known SisReg menu structure (VIDEOFONISTA profile, may vary by profile):
#   li[1] solicitar                   → /cgi-bin/cadweb50?url=/cgi-bin/marcar
#   li[2] Cancelar Solicitações       → /cgi-bin/cons_verificar
#   li[3] cadastro (dropdown)         → Preparos
#   li[4] consulta geral (dropdown)   → CNS
#   li[5] consulta amb (dropdown)     → Solicitações, Arquivo Agendamento, etc.
#   li[6] bpa (dropdown)              → geração de arquivo bpa
#   li[7] Logoff Videofonista         → /cgi-bin/ctrl_videofonista
#
# Feature-specific hrefs (used to find the correct <a> by href attribute):
MENU_HREF_SEARCH = "/cgi-bin/gerenciador_solicitacao"
MENU_HREF_EXPORT = "/cgi-bin/expo_solicitacoes"

# Legacy positional selectors (kept for backward compat, prefer href-based)
MENU_VIDEOFONISTA = "li:nth-child(3) a"
MENU_SOLICITANTE = "li:nth-child(5) > ul > li:nth-child(2) a"

# ── Search (gerenciador_solicitacao) ───────────────────────────────────────────
SEARCH_CGI_PATH = "/cgi-bin/gerenciador_solicitacao"

# ── Listing table ──────────────────────────────────────────────────────────────
LISTING_TABLE = ".table_listagem"
LISTING_ROWS = ".table_listagem tbody tr"

# Column indices in the listing table
COL_CODE = 0
COL_REQUEST_DATE = 1
COL_RISK = 2
COL_PATIENT = 3
# Columns 4, 5 are not used (phone, municipality are extracted differently)
COL_AGE = 6
COL_PROCEDURE = 7
COL_CID = 8
COL_DEPT_SOLICITATION = 9
COL_DEPT_EXECUTE = 10
# Column 11 is not used
COL_STATUS = 12

# Total columns expected per row
LISTING_COLUMN_COUNT = 13

# ── Detail page ────────────────────────────────────────────────────────────────
DETAIL_FICHA = "#fichaAmbulatorial"

# Requesting unit
DETAIL_REQ_UNIT_NAME = "#fichaAmbulatorial tbody:nth-child(1) tr:nth-child(2) td"
DETAIL_REQ_UNIT_CNES = "#fichaAmbulatorial tbody:nth-child(1) tr:nth-child(3) td"

# Patient
DETAIL_PATIENT_CNS = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(2) td:nth-child(2)"
DETAIL_PATIENT_NAME = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(3) td"
DETAIL_PATIENT_BIRTH_DATE = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(4) td"

# Doctor
DETAIL_DOCTOR_NAME = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(2) td"
DETAIL_DOCTOR_CRM = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(3) td"

# Solicitation
DETAIL_SOL_CODE = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(1) td:nth-child(2)"
DETAIL_SOL_STATUS = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(2) td"
DETAIL_SOL_RISK = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(3) td"
DETAIL_SOL_CID = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(4) td"

# Procedure
DETAIL_PROCEDURE_NAME = "#fichaAmbulatorial tbody:nth-child(5) tr:nth-child(2) td"
DETAIL_PROCEDURE_CODE = "#fichaAmbulatorial tbody:nth-child(5) tr:nth-child(3) td"

# Scheduling
DETAIL_APPOINTMENT_DATE = "#fichaAmbulatorial tbody:nth-child(6) tr:nth-child(2) td"
DETAIL_CONFIRMATION_KEY = "#fichaAmbulatorial tbody:nth-child(6) tr:nth-child(3) td"

# Operators
DETAIL_VIDEOCALL_OPERATOR = "#fichaAmbulatorial tbody:nth-child(7) tr:nth-child(2) td"
DETAIL_SOLICITATION_OPERATOR = "#fichaAmbulatorial tbody:nth-child(7) tr:nth-child(3) td"

# Regulatory center
DETAIL_REGULATORY_CENTER = "#fichaAmbulatorial tbody:nth-child(8) tr:nth-child(2) td"
DETAIL_DEPARTMENT = "#fichaAmbulatorial tbody:nth-child(8) tr:nth-child(3) td"
DETAIL_CNES = "#fichaAmbulatorial tbody:nth-child(8) tr:nth-child(4) td"
DETAIL_PRIORITY = "#fichaAmbulatorial tbody:nth-child(8) tr:nth-child(5) td"

# Observations
DETAIL_OBSERVATIONS = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(2) td"

# Phone extraction — primary and fallback selectors
DETAIL_PHONE_PRIMARY = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(16) td"
DETAIL_PHONE_FALLBACK = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(12) td"

# ── CadWeb (Consulta CNS) ────────────────────────────────────────────────────
CADWEB_CGI_PATH = "/cgi-bin/cadweb50"

# ── Schedule export (Arquivo Agendamento) ───────────────────────────────────
EXPORT_CGI_PATH = "/cgi-bin/expo_solicitacoes"
