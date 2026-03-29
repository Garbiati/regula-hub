"""HTML parsers for SisReg listing and detail pages."""

import re

from selectolax.parser import HTMLParser

from regulahub.sisreg.models import AppointmentDetail, AppointmentListing, BestPhone, CadwebPatientData
from regulahub.sisreg.selectors import (
    COL_AGE,
    COL_CID,
    COL_CODE,
    COL_DEPT_EXECUTE,
    COL_DEPT_SOLICITATION,
    COL_PATIENT,
    COL_PROCEDURE,
    COL_REQUEST_DATE,
    COL_RISK,
    COL_STATUS,
    DETAIL_CONFIRMATION_KEY,
    DETAIL_EXEC_UNIT_ADDRESS,
    DETAIL_EXEC_UNIT_ADDRESS_COMPLEMENT,
    DETAIL_EXEC_UNIT_ADDRESS_NUMBER,
    DETAIL_EXEC_UNIT_APPOINTMENT_DATETIME,
    DETAIL_EXEC_UNIT_APPROVAL_DATE,
    DETAIL_EXEC_UNIT_AUTHORIZER,
    DETAIL_EXEC_UNIT_CEP,
    DETAIL_EXEC_UNIT_CNES,
    DETAIL_EXEC_UNIT_MUNICIPALITY,
    DETAIL_EXEC_UNIT_NAME,
    DETAIL_EXEC_UNIT_NEIGHBORHOOD,
    DETAIL_EXEC_UNIT_PHONE,
    DETAIL_EXEC_UNIT_PROFESSIONAL,
    DETAIL_EXEC_UNIT_SLOT,
    DETAIL_JUSTIFICATION,
    DETAIL_PATIENT_BIRTH_DATE,
    DETAIL_PATIENT_CNS,
    DETAIL_PATIENT_NAME,
    DETAIL_PHONE_FALLBACK,
    DETAIL_PHONE_PRIMARY,
    DETAIL_PROCEDURE_CODE,
    DETAIL_PROCEDURE_NAME,
    DETAIL_REQ_UNIT_CNES,
    DETAIL_REQ_UNIT_NAME,
    DETAIL_SOL_CID,
    DETAIL_SOL_CODE,
    DETAIL_SOL_DOCTOR_CPF,
    DETAIL_SOL_DOCTOR_CRM,
    DETAIL_SOL_DOCTOR_NAME,
    DETAIL_SOL_REGULATORY_CENTER,
    DETAIL_SOL_RISK,
    DETAIL_SOL_STATUS,
    DETAIL_SOLICITATION_OPERATOR,
    DETAIL_VIDEOCALL_OPERATOR,
    LISTING_COLUMN_COUNT,
    LISTING_ROWS,
)

# Phone extraction patterns
_DDD_RE = re.compile(r"\((\d{2})\)")
_NUMBER_RE = re.compile(r"(\d{4,5})-(\d{4})")
_MOBILE_RE = re.compile(r"^\(\d{2}\)\s*[6-9]\d{4}-\d{4}$")


def _text(tree: HTMLParser, selector: str) -> str | None:
    """Extract trimmed text from first match, or None."""
    node = tree.css_first(selector)
    if node is None:
        return None
    text = node.text(strip=True)
    return text if text else None


def _cell_text(cells: list, index: int) -> str:
    """Safely get text from a cell list by index."""
    if index >= len(cells):
        return ""
    return cells[index].text(strip=True) or ""


def parse_listing(html: str) -> list[AppointmentListing]:
    """Parse SisReg listing table HTML into AppointmentListing models."""
    tree = HTMLParser(html)
    rows = tree.css(LISTING_ROWS)
    items: list[AppointmentListing] = []

    for row in rows:
        cells = row.css("td")
        if len(cells) < LISTING_COLUMN_COUNT:
            continue

        code = _cell_text(cells, COL_CODE)
        if not code or not code.strip().isdigit():
            continue

        risk_text = _cell_text(cells, COL_RISK)
        try:
            risk = int(risk_text) if risk_text else 0
        except ValueError:
            risk = 0

        items.append(
            AppointmentListing(
                code=code,
                request_date=_cell_text(cells, COL_REQUEST_DATE),
                risk=risk,
                patient_name=_cell_text(cells, COL_PATIENT),
                age=_cell_text(cells, COL_AGE),
                procedure=_cell_text(cells, COL_PROCEDURE),
                cid=_cell_text(cells, COL_CID),
                dept_solicitation=_cell_text(cells, COL_DEPT_SOLICITATION),
                dept_execute=_cell_text(cells, COL_DEPT_EXECUTE),
                status=_cell_text(cells, COL_STATUS),
            )
        )

    return items


def extract_phone(html: str) -> BestPhone | None:
    """Extract best phone number from detail HTML."""
    tree = HTMLParser(html)

    raw_text = _text(tree, DETAIL_PHONE_PRIMARY)
    if not raw_text:
        raw_text = _text(tree, DETAIL_PHONE_FALLBACK)
    if not raw_text:
        return None

    # Clean up
    raw_text = raw_text.replace("(Exibir Lista Detalhada)", "").strip()
    if not raw_text:
        return None

    ddd_match = _DDD_RE.search(raw_text)
    number_match = _NUMBER_RE.search(raw_text)

    ddd = ddd_match.group(1) if ddd_match else ""
    number = f"{number_match.group(1)}-{number_match.group(2)}" if number_match else ""

    formatted = f"({ddd}) {number}" if ddd and number else raw_text
    phone_type = "mobile" if _MOBILE_RE.match(formatted) else "landline"

    return BestPhone(raw=raw_text, ddd=ddd, number=number, phone_type=phone_type)


def _find_labeled_value(tree: HTMLParser, label: str) -> str | None:
    """Find value adjacent to a label in a CadWeb key-value table.

    Patterns handled:
    - <td><b>Label</b></td><td>Value</td>  (same row, next cell)
    - <td><b>Label</b></td></tr><tr><td>Value</td>  (next row, first cell)
    """
    for node in tree.css("b"):
        text = node.text(strip=True) or ""
        if text == label:
            # The <b> is inside a <td> — get sibling <td> or next-row <td>
            td = node.parent
            if td is None or td.tag != "td":
                continue
            # Try next sibling <td> in the same <tr>
            sibling = td.next
            while sibling is not None:
                if hasattr(sibling, "tag") and sibling.tag == "td":
                    value = sibling.text(strip=True)
                    if value and value != "---":
                        return value
                    break
                sibling = sibling.next
            # Try next row's first <td> (pattern: label in one row, value in next)
            tr = td.parent
            if tr is not None and tr.tag == "tr":
                next_node = tr.next
                while next_node is not None:
                    if hasattr(next_node, "tag") and next_node.tag == "tr":
                        first_td = next_node.css_first("td")
                        if first_td:
                            value = first_td.text(strip=True)
                            if value and value != "---":
                                return value
                        break
                    next_node = next_node.next
    return None


def _extract_cadweb_phone(tree: HTMLParser) -> tuple[str | None, str | None, str | None]:
    """Extract phone from CONTATOS table. Prefer CELULAR type.

    Returns (phone_type, ddd, number).
    """
    phones: list[tuple[str, str, str]] = []

    # Find tables with phone data — look for header row with "Tipo Telefone"
    for table in tree.css("table"):
        rows = table.css("tr")
        is_phone_table = False
        for row in rows:
            headers = row.css("th")
            if headers and any("Tipo Telefone" in (h.text(strip=True) or "") for h in headers):
                is_phone_table = True
                continue
            if is_phone_table:
                cells = row.css("td")
                if len(cells) >= 3:
                    ptype = (cells[0].text(strip=True) or "").strip()
                    ddd = (cells[1].text(strip=True) or "").strip()
                    number = (cells[2].text(strip=True) or "").strip()
                    # Clean DDD — remove parentheses
                    ddd = re.sub(r"[()]", "", ddd).strip()
                    # Clean number — remove dash for storage consistency
                    if ptype and ddd and number:
                        phones.append((ptype, ddd, number))

    if not phones:
        return None, None, None

    # Prefer CELULAR
    for ptype, ddd, number in phones:
        if ptype.upper() == "CELULAR":
            return ptype, ddd, number

    # Fallback to first available
    return phones[0]


def _clean_cpf(cpf: str | None) -> str | None:
    """Remove formatting from CPF. '335.255.282-72' → '33525528272'."""
    if not cpf:
        return None
    cleaned = re.sub(r"[.\-]", "", cpf.strip())
    return cleaned if len(cleaned) == 11 and cleaned.isdigit() else None


def parse_cadweb(html: str) -> CadwebPatientData:
    """Parse CadWeb patient lookup result page."""
    tree = HTMLParser(html)

    cpf = _find_labeled_value(tree, "CPF:")
    mother_name = _find_labeled_value(tree, "Nome da Mãe:")
    father_name = _find_labeled_value(tree, "Nome do Pai:")
    sex = _find_labeled_value(tree, "Sexo:")

    phone_type, phone_ddd, phone_number = _extract_cadweb_phone(tree)

    return CadwebPatientData(
        cpf=_clean_cpf(cpf),
        mother_name=mother_name,
        father_name=father_name,
        sex=sex,
        phone_type=phone_type,
        phone_ddd=phone_ddd,
        phone_number=phone_number,
    )


def parse_detail(html: str) -> AppointmentDetail:
    """Parse SisReg detail page HTML (12-tbody fichaAmbulatorial) into AppointmentDetail model."""
    tree = HTMLParser(html)

    phone = extract_phone(html)

    return AppointmentDetail(
        # tbody 1 — Confirmation key
        confirmation_key=_text(tree, DETAIL_CONFIRMATION_KEY),
        # tbody 2 — Requesting unit
        req_unit_name=_text(tree, DETAIL_REQ_UNIT_NAME),
        req_unit_cnes=_text(tree, DETAIL_REQ_UNIT_CNES),
        solicitation_operator=_text(tree, DETAIL_SOLICITATION_OPERATOR),
        videocall_operator=_text(tree, DETAIL_VIDEOCALL_OPERATOR),
        # tbody 3 — Executing unit
        exec_unit_name=_text(tree, DETAIL_EXEC_UNIT_NAME),
        exec_unit_cnes=_text(tree, DETAIL_EXEC_UNIT_CNES),
        exec_unit_authorizer=_text(tree, DETAIL_EXEC_UNIT_AUTHORIZER),
        exec_unit_slot=_text(tree, DETAIL_EXEC_UNIT_SLOT),
        exec_unit_address=_text(tree, DETAIL_EXEC_UNIT_ADDRESS),
        exec_unit_address_number=_text(tree, DETAIL_EXEC_UNIT_ADDRESS_NUMBER),
        exec_unit_address_complement=_text(tree, DETAIL_EXEC_UNIT_ADDRESS_COMPLEMENT),
        exec_unit_approval_date=_text(tree, DETAIL_EXEC_UNIT_APPROVAL_DATE),
        exec_unit_phone=_text(tree, DETAIL_EXEC_UNIT_PHONE),
        exec_unit_cep=_text(tree, DETAIL_EXEC_UNIT_CEP),
        exec_unit_neighborhood=_text(tree, DETAIL_EXEC_UNIT_NEIGHBORHOOD),
        exec_unit_municipality=_text(tree, DETAIL_EXEC_UNIT_MUNICIPALITY),
        exec_unit_professional=_text(tree, DETAIL_EXEC_UNIT_PROFESSIONAL),
        exec_unit_appointment_datetime=_text(tree, DETAIL_EXEC_UNIT_APPOINTMENT_DATETIME),
        # tbody 4 — Patient
        patient_cns=_text(tree, DETAIL_PATIENT_CNS),
        patient_name=_text(tree, DETAIL_PATIENT_NAME),
        patient_birth_date=_text(tree, DETAIL_PATIENT_BIRTH_DATE),
        patient_phone=phone.raw if phone else None,
        # tbody 6 — Justification
        justification=_text(tree, DETAIL_JUSTIFICATION),
        # tbody 9 — Solicitation
        sol_code=_text(tree, DETAIL_SOL_CODE),
        sol_status=_text(tree, DETAIL_SOL_STATUS),
        sol_doctor_cpf=_text(tree, DETAIL_SOL_DOCTOR_CPF),
        sol_doctor_crm=_text(tree, DETAIL_SOL_DOCTOR_CRM),
        sol_doctor_name=_text(tree, DETAIL_SOL_DOCTOR_NAME),
        sol_cid=_text(tree, DETAIL_SOL_CID),
        sol_risk=_text(tree, DETAIL_SOL_RISK),
        sol_regulatory_center=_text(tree, DETAIL_SOL_REGULATORY_CENTER),
        # tbody 11 — Procedure
        procedure_name=_text(tree, DETAIL_PROCEDURE_NAME),
        procedure_code=_text(tree, DETAIL_PROCEDURE_CODE),
        # Phone
        best_phone=phone,
    )
