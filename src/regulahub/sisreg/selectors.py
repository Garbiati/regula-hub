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

# ── Detail page (fichaAmbulatorial) ───────────────────────────────────────────
# Validated against REAL SisReg HTML captured 2026-03-29.
# The lexbor parser creates 12 implicit tbodies from the mixed HTML structure:
#   tbody 1: Chave de Confirmação (implicit, from <tr> before first explicit <tbody>)
#   tbody 2: Unidade Solicitante (explicit FichaCompleta)
#   tbody 3: Unidade Executante (implicit, from <tr> between tbodies)
#   tbody 4: Dados do Paciente — ficha completa (explicit FichaCompleta)
#   tbody 5: Dados do Paciente — ficha reduzida (explicit FichaReduzida, display:none)
#   tbody 6: Laudo / Justificativa (explicit FichaCompleta)
#   tbody 7: Histórico de Troca de Procedimentos (explicit FichaCompleta)
#   tbody 8: Header "Dados da Solicitação" (implicit)
#   tbody 9: Dados da Solicitação — ficha completa (explicit FichaCompleta)
#   tbody 10: Dados da Solicitação — ficha reduzida (explicit FichaReduzida)
#   tbody 11: Procedimentos Solicitados (implicit)
#   tbody 12: empty (explicit FichaCompleta)
DETAIL_FICHA = "#fichaAmbulatorial"

# tbody 1 — Chave de Confirmação
DETAIL_CONFIRMATION_KEY = "#fichaAmbulatorial tbody:nth-child(1) tr:nth-child(2) td"

# tbody 2 — Unidade Solicitante (row 1=title, row 2=labels, row 3=values)
DETAIL_REQ_UNIT_NAME = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(3) td:nth-child(1)"
DETAIL_REQ_UNIT_CNES = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(3) td:nth-child(2)"
DETAIL_SOLICITATION_OPERATOR = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(3) td:nth-child(3)"
DETAIL_VIDEOCALL_OPERATOR = "#fichaAmbulatorial tbody:nth-child(2) tr:nth-child(3) td:nth-child(4)"

# tbody 3 — Unidade Executante (critical for integration routing)
# Row layout: 1=title, 2=labels, 3=values, 4=labels, 5=values, 6=labels, 7=values, 8=labels, 9=values
DETAIL_EXEC_UNIT_NAME = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(3) td:nth-child(1)"
DETAIL_EXEC_UNIT_CNES = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(3) td:nth-child(2)"
DETAIL_EXEC_UNIT_AUTHORIZER = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(3) td:nth-child(3)"
DETAIL_EXEC_UNIT_SLOT = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(3) td:nth-child(4)"
DETAIL_EXEC_UNIT_ADDRESS = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(5) td:nth-child(1)"
DETAIL_EXEC_UNIT_ADDRESS_NUMBER = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(5) td:nth-child(2)"
DETAIL_EXEC_UNIT_ADDRESS_COMPLEMENT = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(5) td:nth-child(3)"
DETAIL_EXEC_UNIT_APPROVAL_DATE = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(5) td:nth-child(4)"
DETAIL_EXEC_UNIT_PHONE = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(7) td:nth-child(1)"
DETAIL_EXEC_UNIT_CEP = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(7) td:nth-child(2)"
DETAIL_EXEC_UNIT_NEIGHBORHOOD = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(7) td:nth-child(3)"
DETAIL_EXEC_UNIT_MUNICIPALITY = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(7) td:nth-child(4)"
DETAIL_EXEC_UNIT_PROFESSIONAL = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(9) td:nth-child(1)"
DETAIL_EXEC_UNIT_APPOINTMENT_DATETIME = "#fichaAmbulatorial tbody:nth-child(3) tr:nth-child(9) td:nth-child(2)"

# tbody 4 — Dados do Paciente (ficha completa)
# Row layout: 1=CNS label, 2=CNS value, 3=labels, 4=values(name,social,birth,sex)
DETAIL_PATIENT_CNS = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(2) td"
DETAIL_PATIENT_NAME = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(4) td:nth-child(1)"
DETAIL_PATIENT_BIRTH_DATE = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(4) td:nth-child(3)"

# tbody 6 — Laudo / Justificativa
DETAIL_JUSTIFICATION = "#fichaAmbulatorial tbody:nth-child(6) tr:nth-child(2) td"

# tbody 9 — Dados da Solicitação (ficha completa)
# Row layout: 1=labels(code,status), 2=values, 3=labels(cpf,crm,name,slot), 4=values,
#             5=labels(diag,cid,risk), 6=values, 7=label(central), 8=value
DETAIL_SOL_CODE = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(2) td:nth-child(1)"
DETAIL_SOL_STATUS = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(2) td:nth-child(2)"
DETAIL_SOL_DOCTOR_CPF = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(4) td:nth-child(1)"
DETAIL_SOL_DOCTOR_CRM = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(4) td:nth-child(2)"
DETAIL_SOL_DOCTOR_NAME = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(4) td:nth-child(3)"
DETAIL_SOL_CID = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(6) td:nth-child(2)"
DETAIL_SOL_RISK = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(6) td:nth-child(3)"
DETAIL_SOL_REGULATORY_CENTER = "#fichaAmbulatorial tbody:nth-child(9) tr:nth-child(8) td"

# tbody 11 — Procedimentos Solicitados
# Row layout: 1=labels(proc,unif,int), 2=values
DETAIL_PROCEDURE_NAME = "#fichaAmbulatorial tbody:nth-child(11) tr:nth-child(2) td:nth-child(1)"
DETAIL_PROCEDURE_CODE = "#fichaAmbulatorial tbody:nth-child(11) tr:nth-child(2) td:nth-child(2)"

# Phone extraction — in patient section (tbody 4)
DETAIL_PHONE_PRIMARY = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(16) td"
DETAIL_PHONE_FALLBACK = "#fichaAmbulatorial tbody:nth-child(4) tr:nth-child(14) td"

# ── CadWeb (Consulta CNS) ────────────────────────────────────────────────────
CADWEB_CGI_PATH = "/cgi-bin/cadweb50"

# ── Schedule export (Arquivo Agendamento) ───────────────────────────────────
EXPORT_CGI_PATH = "/cgi-bin/expo_solicitacoes"
