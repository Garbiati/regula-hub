"""CADSUS (SUS patient registry) async HTTP client — SOAP/HL7 v3 integration."""

import logging
import time
import uuid
from datetime import datetime
from xml.etree import ElementTree as ET  # noqa: S405  # nosec B405 — trusted CADSUS gov API

import httpx
from pydantic import BaseModel

from regulahub.config import CadsusSettings, get_cadsus_settings

logger = logging.getLogger(__name__)

# ── HL7 v3 OID constants (from ptm-auth-server XmlUtils.cs) ──────────────────
CPF_CODE = "2.16.840.1.113883.13.237"
CNS_CODE = "2.16.840.1.113883.13.236"
CNS_TYPE_CODE = "2.16.840.1.113883.13.236.1"
CNS_DEFINITIVE = "D"
MOTHER_NAME_CODE = "PRN"
FATHER_NAME_CODE = "NPRN"
EMAIL_CODE = "NET"
PHONE_CODES = ("ORN", "HP")
NOT_FOUND_CODE = "NF"

# XML namespaces
NS_SOAP = "http://www.w3.org/2003/05/soap-envelope"
NS_HL7 = "urn:hl7-org:v3"


class CadsusAddress(BaseModel):
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    cep: str | None = None
    pais: str | None = None


class CadsusPatientData(BaseModel):
    cpf: str | None = None
    cns: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    birth_date: str | None = None
    mother_name: str | None = None
    father_name: str | None = None
    race: str | None = None
    address: CadsusAddress | None = None
    match_score: int = 0


class CadsusClient:
    """Async client for the Brazilian CADSUS patient registry (SOAP/HL7 v3)."""

    def __init__(self, settings: CadsusSettings | None = None) -> None:
        self._settings = settings or get_cadsus_settings()
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._ssl_ctx: object | None = None
        self._ssl_ctx_built = False

    def _get_ssl_context(self) -> object | None:
        """Lazily build and cache the SSL context."""
        if not self._ssl_ctx_built:
            self._ssl_ctx = self._build_ssl_context()
            self._ssl_ctx_built = True
        return self._ssl_ctx

    async def get_patient_by_cns(self, cns: str, *, max_retries: int = 3) -> CadsusPatientData | None:
        """Look up patient data by CNS in the CADSUS registry.

        Retries up to max_retries times on 401/429 (rate limit) with exponential backoff.
        Returns None if patient not found or on persistent failure.
        """
        if not self._settings.cadsus_enabled:
            return None

        import asyncio

        for attempt in range(max_retries):
            try:
                token = await self._ensure_token()
                soap_body = self._build_soap_request(cns, is_cpf=False)

                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as http:
                    resp = await http.post(
                        f"{self._settings.cadsus_services_url}/cadsus/v2/PDQSupplierJWT",
                        content=soap_body.encode("utf-8"),
                        headers={
                            "Content-Type": "application/soap+xml; charset=utf-8",
                            "Authorization": f"jwt {token}",
                        },
                    )

                if resp.status_code in (401, 429, 503):
                    if attempt < max_retries - 1:
                        delay = (attempt + 1) * 2  # 2s, 4s, 6s
                        logger.info(
                            "CADSUS rate limited (status %d), retry %d/%d in %ds",
                            resp.status_code, attempt + 1, max_retries, delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.warning("CADSUS failed after %d retries for CNS (status %d)", max_retries, resp.status_code)
                    return None

                if not resp.is_success:
                    logger.warning("CADSUS SOAP failed: status=%d", resp.status_code)
                    return None

                return self._parse_soap_response(resp.text)

            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep((attempt + 1) * 2)
                    continue
                logger.exception("CADSUS lookup failed for patient after %d retries", max_retries)
                return None

        return None

    def _build_ssl_context(self) -> object | None:
        """Build SSL context with client certificate for mTLS if configured."""
        cert_path = self._settings.cadsus_cert_path
        if not cert_path:
            return None

        import ssl
        import tempfile

        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12

        with open(cert_path, "rb") as f:
            pfx_data = f.read()

        password = self._settings.cadsus_cert_password.encode() if self._settings.cadsus_cert_password else None
        private_key, certificate, chain = pkcs12.load_key_and_certificates(pfx_data, password)

        # Write PEM files to temp — keep them alive for the lifetime of this client
        cert_f = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)  # noqa: SIM115
        cert_f.write(certificate.public_bytes(Encoding.PEM))
        if chain:
            for ca_cert in chain:
                cert_f.write(ca_cert.public_bytes(Encoding.PEM))
        cert_f.close()

        key_f = tempfile.NamedTemporaryFile(suffix=".pem", delete=False)  # noqa: SIM115
        key_f.write(private_key.private_bytes(
            Encoding.PEM, format=PrivateFormat.TraditionalOpenSSL, encryption_algorithm=NoEncryption(),
        ))
        key_f.close()

        ctx = ssl.create_default_context()
        ctx.load_cert_chain(cert_f.name, key_f.name)

        # Store paths for cleanup (files must persist while ssl context is used)
        self._temp_cert_path = cert_f.name
        self._temp_key_path = key_f.name

        logger.info("CADSUS mTLS SSL context built from %s", cert_path)
        return ctx

    async def _ensure_token(self) -> str:
        """Obtain or refresh the JWT token from the CADSUS auth endpoint.

        Uses client certificate (mTLS) if CADSUS_CERT_PATH is configured.
        """
        now = time.monotonic()
        margin = self._settings.cadsus_token_margin_seconds

        if self._token and now < (self._token_expires_at - margin):
            return self._token

        ssl_ctx = self._get_ssl_context()
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0), verify=ssl_ctx or True) as http:
            resp = await http.get(f"{self._settings.cadsus_auth_url}/api/osb/token")
            resp.raise_for_status()

        data = resp.json()
        self._token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._token_expires_at = now + expires_in

        logger.info("CADSUS token refreshed, expires in %d seconds", expires_in)
        return self._token

    def _build_soap_request(self, document: str, *, is_cpf: bool = False) -> str:
        """Build SOAP XML PRPA_IN201305UV02 request for patient lookup."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:17]  # noqa: DTZ005
        query_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        root_code = CPF_CODE if is_cpf else CNS_CODE

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="{NS_SOAP}" xmlns:urn="{NS_HL7}">
  <soap:Body>
    <urn:PRPA_IN201305UV02 ITSVersion="XML_1.0">
      <urn:id root="2.16.840.1.113883.4.714" extension="{message_id}"/>
      <urn:creationTime value="{timestamp}"/>
      <urn:interactionId root="2.16.840.1.113883.1.6" extension="PRPA_IN201305UV02"/>
      <urn:processingCode code="T"/>
      <urn:processingModeCode code="T"/>
      <urn:acceptAckCode code="AL"/>
      <urn:receiver typeCode="RCV">
        <urn:device classCode="DEV" determinerCode="INSTANCE">
          <urn:id root="2.16.840.1.113883.3.72.6.5.100.85"/>
        </urn:device>
      </urn:receiver>
      <urn:sender typeCode="SND">
        <urn:device classCode="DEV" determinerCode="INSTANCE">
          <urn:id root="2.16.840.1.113883.3.72.6.2"/>
          <urn:name>CADSUS</urn:name>
        </urn:device>
      </urn:sender>
      <urn:controlActProcess classCode="CACT" moodCode="EVN">
        <urn:code code="PRPA_TE201305UV02" codeSystem="2.16.840.1.113883.1.6"/>
        <urn:queryByParameter>
          <urn:queryId root="1.2.840.114350.1.13.28.1.18.5.999" extension="{query_id}"/>
          <urn:statusCode code="new"/>
          <urn:responseModalityCode code="R"/>
          <urn:responsePriorityCode code="I"/>
          <urn:parameterList>
            <urn:livingSubjectId>
              <urn:value root="{root_code}" extension="{document}"/>
              <urn:semanticsText>LivingSubject.id</urn:semanticsText>
            </urn:livingSubjectId>
          </urn:parameterList>
        </urn:queryByParameter>
      </urn:controlActProcess>
    </urn:PRPA_IN201305UV02>
  </soap:Body>
</soap:Envelope>"""

    def _parse_soap_response(self, xml_text: str) -> CadsusPatientData | None:
        """Parse HL7 v3 SOAP response and extract patient data."""
        # Strip BOM if present
        xml_text = xml_text.lstrip("\ufeff\u200b")

        try:
            root = ET.fromstring(xml_text)  # noqa: S314  # nosec B314
        except ET.ParseError:
            logger.warning("Failed to parse CADSUS XML response")
            return None

        # Check queryResponseCode
        query_ack = root.find(f".//{{{NS_HL7}}}queryAck")
        if query_ack is not None:
            response_code_el = query_ack.find(f"{{{NS_HL7}}}queryResponseCode")
            if response_code_el is not None and response_code_el.get("code") == NOT_FOUND_CODE:
                return None

        # Find patient element
        patient = root.find(f".//{{{NS_HL7}}}patient")
        if patient is None:
            return None

        data = CadsusPatientData()
        patient_person = patient.find(f"{{{NS_HL7}}}patientPerson")
        if patient_person is None:
            return data

        # Name
        name_el = patient_person.find(f"{{{NS_HL7}}}name")
        if name_el is not None:
            given = name_el.find(f"{{{NS_HL7}}}given")
            if given is not None and given.text:
                parts = given.text.strip().split(" ", 1)
                data.first_name = parts[0]
                data.last_name = parts[1] if len(parts) > 1 else ""

        # Telecom (phone, email)
        for telecom in patient_person.findall(f"{{{NS_HL7}}}telecom"):
            use = telecom.get("use", "")
            value = telecom.get("value", "")
            if use == EMAIL_CODE and not data.email:
                data.email = value
            elif use in PHONE_CODES and not data.phone:
                data.phone = value

        # Gender
        gender_el = patient_person.find(f"{{{NS_HL7}}}administrativeGenderCode")
        if gender_el is not None:
            data.gender = gender_el.get("code")

        # Birth date
        birth_el = patient_person.find(f"{{{NS_HL7}}}birthTime")
        if birth_el is not None:
            bv = birth_el.get("value", "")
            if len(bv) >= 8:
                try:
                    dt = datetime.strptime(bv[:8], "%Y%m%d")  # noqa: DTZ007
                    data.birth_date = dt.strftime("%d/%m/%Y")
                except ValueError:
                    pass

        # Address
        addr_el = patient_person.find(f"{{{NS_HL7}}}addr")
        if addr_el is not None:
            data.address = CadsusAddress(
                logradouro=self._el_text(addr_el, "streetName"),
                numero=self._el_text(addr_el, "houseNumber"),
                bairro=self._el_text(addr_el, "additionalLocator"),
                cidade=self._el_text(addr_el, "city"),
                cep=self._el_text(addr_el, "postalCode"),
                pais=self._el_text(addr_el, "country"),
            )

        # Race
        race_el = patient_person.find(f"{{{NS_HL7}}}raceCode")
        if race_el is not None:
            data.race = race_el.get("code")

        # Relationships (mother, father)
        for rel in patient_person.findall(f"{{{NS_HL7}}}personalRelationship"):
            code_el = rel.find(f"{{{NS_HL7}}}code")
            code = code_el.get("code", "") if code_el is not None else ""
            holder = rel.find(f"{{{NS_HL7}}}relationshipHolder1")
            if holder is not None:
                holder_name_el = holder.find(f"{{{NS_HL7}}}name")
                if holder_name_el is not None:
                    given_el = holder_name_el.find(f"{{{NS_HL7}}}given")
                    holder_name = given_el.text if given_el is not None and given_el.text else None
                    if code == MOTHER_NAME_CODE and not data.mother_name:
                        data.mother_name = holder_name
                    elif code == FATHER_NAME_CODE and not data.father_name:
                        data.father_name = holder_name

        # CPF from asOtherIDs
        for other_id in patient_person.findall(f"{{{NS_HL7}}}asOtherIDs"):
            for id_el in other_id.findall(f"{{{NS_HL7}}}id"):
                if id_el.get("root") == CPF_CODE:
                    data.cpf = id_el.get("extension")

        # CNS (prefer definitive)
        cns_entries = []
        for other_id in patient_person.findall(f"{{{NS_HL7}}}asOtherIDs"):
            ids = other_id.findall(f"{{{NS_HL7}}}id")
            cns_number = None
            cns_type = None
            for id_el in ids:
                if id_el.get("root") == CNS_CODE:
                    cns_number = id_el.get("extension")
                elif id_el.get("root") == CNS_TYPE_CODE:
                    cns_type = id_el.get("extension")
            if cns_number and cns_type:
                cns_entries.append((cns_number, cns_type))

        # Sort: definitive first
        cns_entries.sort(key=lambda x: x[1] != CNS_DEFINITIVE)
        if cns_entries:
            data.cns = cns_entries[0][0]

        # Match score
        match_obs = patient.find(f".//{{{NS_HL7}}}queryMatchObservation")
        if match_obs is not None:
            value_el = match_obs.find(f"{{{NS_HL7}}}value")
            if value_el is not None:
                import contextlib

                with contextlib.suppress(ValueError):
                    data.match_score = int(value_el.get("value", "0"))

        return data

    @staticmethod
    def _el_text(parent: ET.Element, local_name: str) -> str | None:
        """Extract text from a child element by local name in HL7 namespace."""
        el = parent.find(f"{{{NS_HL7}}}{local_name}")
        return el.text if el is not None and el.text else None
