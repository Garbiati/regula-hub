"""HTTP client for pushing enriched appointments to integration systems.

Implements the Saude AM Digital integration flow:
find_patient_by_cpf → register/update_patient → list_doctors → check_appointment → create_appointment

# TODO: refactor — Much of this is Saude AM Digital specific (headers, payloads, doctor matching).
# When adding other integration targets, extract a base class and create provider-specific subclasses.
"""

import dataclasses
import logging
import re
import unicodedata
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

MANAUS_TZ = ZoneInfo("America/Manaus")


@dataclasses.dataclass
class PushResult:
    """Result of pushing a single appointment to the integration system."""

    code: str
    success: bool
    patient_id: str = ""
    appointment_id: str = ""
    is_new_account: bool = False
    patient_created: bool = False
    patient_updated: bool = False
    appointment_created: bool = False
    appointment_skipped: bool = False
    error: str | None = None
    error_category: str = ""  # patient, appointment, mapping, data, network


@dataclasses.dataclass
class BatchPushResult:
    """Aggregated result of pushing a batch of appointments."""

    total: int = 0
    pushed: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[PushResult] = dataclasses.field(default_factory=list)


def normalize_name(name: str) -> str:
    """Normalize a name for comparison: remove accents, special chars, lowercase.

    Matches the .NET NormalizeName() from ptm-regulation-service.
    """
    if not name:
        return ""
    # Remove accents (NFD decomposition + strip combining marks)
    normalized = unicodedata.normalize("NFD", name)
    stripped = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    # Remove special characters except spaces and alphanumeric
    stripped = re.sub(r"[^a-zA-Z0-9\s]", "", stripped)
    # Collapse multiple spaces
    stripped = re.sub(r"\s+", " ", stripped)
    return stripped.strip().lower()


class IntegrationPushClient:
    """HTTP client that pushes enriched appointment data to Saude AM Digital.

    Uses Core API and Auth API with X-API-KEY + PTM-Client-Domain authentication.
    # TODO: refactor — Extract base class for provider-agnostic integration.
    """

    def __init__(
        self,
        core_api_base_url: str,
        auth_api_base_url: str,
        api_key: str,
        health_center: str = "SAUDEAMDIGITAL",  # TODO: refactor — provider specific
        timeout: float = 30.0,
    ) -> None:
        self._core_base = core_api_base_url.rstrip("/")
        self._auth_base = auth_api_base_url.rstrip("/")
        self._api_key = api_key
        self._health_center = health_center
        self._timeout = timeout
        self._doctors_cache: list[dict] | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "IntegrationPushClient":
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": self._api_key,
            "PTM-Client-Domain": self._health_center,
        }
        self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── Patient operations ──────────────────────────────────────────────

    async def find_patient_by_cpf(self, cpf: str) -> str | None:
        """Find patient by CPF. Returns patient UUID or None."""
        if not cpf:
            return None
        try:
            resp = await self._client.get(f"{self._core_base}/integration/patient/idbycpf", params={"cpf": cpf})
            if resp.status_code == 200:
                data = resp.json()
                # Response is a UUID string directly or {"id": "uuid"}
                if isinstance(data, str) and data and data != "00000000-0000-0000-0000-000000000000":
                    return data
                if isinstance(data, dict):
                    pid = data.get("id", data.get("patientId", ""))
                    if pid and pid != "00000000-0000-0000-0000-000000000000":
                        return str(pid)
            return None
        except Exception:
            logger.warning("find_patient_by_cpf failed")
            return None

    async def register_patient(self, data: dict, group_id: str, is_new: bool = True) -> str | None:
        """Register a new patient in Auth API. Returns patient UUID or None.

        # TODO: refactor — Auth API endpoint and payload are Saude AM Digital specific.
        """
        payload = {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "date_of_birth": data.get("date_of_birth", ""),  # dd/MM/yyyy
            "gender": "unknown",  # TODO: refactor — hardcoded for Saude AM Digital
            "cpf": data.get("cpf", ""),
            "cns": data.get("cns", ""),
            "phone": data.get("phone", ""),
            "email": None,
            "group_id": group_id,  # TODO: refactor — Saude AM Digital specific
        }
        try:
            resp = await self._client.post(f"{self._auth_base}/integration/patient/register", json=payload)
            if resp.status_code in (200, 201):
                result = resp.json()
                return str(result) if isinstance(result, str) else str(result.get("id", result.get("patientId", "")))
            dob = payload.get("date_of_birth", "")
            logger.warning(
                "register_patient failed: %s %s | dob=%s cpf=%s",
                resp.status_code,
                resp.text[:300],
                dob,
                payload.get("cpf", "")[:6],
            )
            return None
        except Exception:
            logger.warning("register_patient request failed")
            return None

    async def update_patient(self, patient_id: str, data: dict) -> bool:
        """Update existing patient in Core API. Returns True if successful."""
        payload = {
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "mothers_name": data.get("mothers_name", ""),
            "phone": data.get("phone", ""),
        }
        try:
            resp = await self._client.patch(f"{self._core_base}/integration/patient/{patient_id}", json=payload)
            return resp.status_code == 200
        except Exception:
            logger.warning("update_patient failed for patient %s", patient_id[:8])
            return False

    # ── Doctor operations ───────────────────────────────────────────────

    async def list_doctors(self) -> list[dict]:
        """List doctors from Core API. Cached per execution."""
        if self._doctors_cache is not None:
            return self._doctors_cache
        try:
            resp = await self._client.get(f"{self._core_base}/integration/doctor")
            if resp.status_code == 200:
                data = resp.json()
                self._doctors_cache = data if isinstance(data, list) else data.get("items", [])
            else:
                self._doctors_cache = []
        except Exception:
            logger.warning("list_doctors request failed")
            self._doctors_cache = []
        return self._doctors_cache

    async def resolve_doctor_id(self, doctor_name: str) -> str | None:
        """Resolve doctor ID by normalized name matching."""
        if not doctor_name:
            return None
        doctors = await self.list_doctors()
        target = normalize_name(doctor_name)
        for doc in doctors:
            doc_name = doc.get("doctor_name", doc.get("doctorName", doc.get("name", "")))
            if normalize_name(doc_name) == target:
                return str(doc.get("doctor_id", doc.get("doctorId", doc.get("id", ""))))
        return None

    # ── Appointment operations ──────────────────────────────────────────

    async def check_appointment_exists(self, external_id: str) -> str | None:
        """Check if appointment already exists by external ID. Returns appointment UUID or None."""
        try:
            resp = await self._client.get(f"{self._core_base}/integration/appointment/external/{external_id}")
            if resp.status_code == 200:
                data = resp.json()
                return str(data.get("id", "")) if isinstance(data, dict) else None
            return None
        except Exception:
            return None

    async def create_appointment(self, data: dict, is_new_account: bool = False) -> str | None:
        """Create appointment in Core API. Returns appointment UUID or None.

        On 409 (doctor preference conflict), retries without doctor preference.
        """
        headers = {
            "ptm-send-reminder": "true",
            "ptm-new-account": str(is_new_account).lower(),
        }
        try:
            resp = await self._client.post(
                f"{self._core_base}/integration/appointment",
                json=data,
                headers=headers,
            )
            if resp.status_code in (200, 201):
                result = resp.json()
                return str(result.get("id", "")) if isinstance(result, dict) else str(result)

            # 409 = doctor preference conflict → retry without doctor
            if resp.status_code == 409 and data.get("preference_of_doctor_id"):
                logger.info("Appointment 409 conflict, retrying without doctor preference")
                data_no_doctor = {**data, "preference_of_doctor_id": None}
                resp2 = await self._client.post(
                    f"{self._core_base}/integration/appointment",
                    json=data_no_doctor,
                    headers=headers,
                )
                if resp2.status_code in (200, 201):
                    result = resp2.json()
                    return str(result.get("id", "")) if isinstance(result, dict) else str(result)

            # 500 with "Invalid sender name" for PRESENCIAL → retry as ONLINE
            is_sender_error = resp.status_code == 500 and "Invalid sender name" in resp.text
            if is_sender_error and data.get("preference_of_service") == "PRESENCIAL":
                logger.info("Appointment 500 Invalid sender name, retrying as ONLINE")
                data_online = {**data, "preference_of_service": "ONLINE"}
                resp3 = await self._client.post(
                    f"{self._core_base}/integration/appointment",
                    json=data_online,
                    headers=headers,
                )
                if resp3.status_code in (200, 201):
                    result = resp3.json()
                    return str(result.get("id", "")) if isinstance(result, dict) else str(result)

            logger.warning("create_appointment failed: %s %s", resp.status_code, resp.text[:500])
            return None
        except Exception as exc:
            logger.warning("create_appointment request failed: %s", exc)
            return None

    # ── Full flow per appointment ───────────────────────────────────────

    async def process_appointment(self, appointment: dict) -> PushResult:
        """Execute the full integration flow for a single enriched appointment.

        Flow: find/register patient → resolve doctor → check duplicate → create appointment
        """
        code = appointment.get("code", "unknown")
        result = PushResult(code=code, success=False)

        try:
            # ── Step 1: Find or register patient ──
            cpf = appointment.get("patient_cpf", "")
            group_id = appointment.get("group_id", "")
            if not group_id:
                result.error = "Missing group_id (department not mapped)"
                result.error_category = "mapping"
                return result

            patient_id = None
            is_new_account = False

            if cpf:
                patient_id = await self.find_patient_by_cpf(cpf)

            if patient_id:
                # Update existing patient
                await self.update_patient(
                    patient_id,
                    {
                        "first_name": appointment.get("patient_first_name", ""),
                        "last_name": appointment.get("patient_last_name", ""),
                        "mothers_name": appointment.get("patient_mother_name", ""),
                        "phone": appointment.get("patient_phone", ""),
                    },
                )
                result.patient_updated = True
            else:
                # Register new patient
                birth_date = appointment.get("patient_birth_date", "")
                if not birth_date:
                    result.error = "Missing patient birth date"
                    result.error_category = "data"
                    return result

                patient_id = await self.register_patient(
                    {
                        "first_name": appointment.get("patient_first_name", ""),
                        "last_name": appointment.get("patient_last_name", ""),
                        "date_of_birth": birth_date,
                        "cpf": cpf,
                        "cns": appointment.get("patient_cns", ""),
                        "phone": appointment.get("patient_phone", "00000000000"),
                    },
                    group_id=group_id,
                )
                if not patient_id:
                    result.error = "Failed to register patient"
                    result.error_category = "patient"
                    return result
                result.patient_created = True
                is_new_account = True

            result.patient_id = patient_id
            result.is_new_account = is_new_account

            # ── Step 2: Resolve doctor (non-blocking) ──
            doctor_name = appointment.get("doctor_name", "")
            doctor_id = await self.resolve_doctor_id(doctor_name)
            if not doctor_id and doctor_name:
                logger.info("Doctor not found: %s (non-blocking)", doctor_name[:30])

            # ── Step 3: Check for existing appointment (idempotency) ──
            external_id = appointment.get("external_id", "")
            if not external_id:
                result.error = "Missing external_id"
                result.error_category = "data"
                return result

            existing = await self.check_appointment_exists(external_id)
            if existing:
                result.success = True
                result.appointment_skipped = True
                result.appointment_id = existing
                return result

            # ── Step 4: Create appointment ──
            # TODO: refactor — Payload structure is Saude AM Digital specific
            appointment_data = {
                "patient_id": patient_id,
                "group_id": group_id,
                "external_id": external_id,
                "start_date": appointment.get("start_date", ""),
                "end_date": appointment.get("end_date", ""),
                "specialty": appointment.get("work_scale_name", ""),
                "preference_of_service": appointment.get("preference_of_service", "ONLINE"),
                "preference_of_doctor_id": doctor_id,
                "location_of_service": appointment.get("location_of_service", ""),
                "regulation_code": code,
                "confirmation_key": appointment.get("confirmation_key", ""),
                "canceled": False,
            }

            appt_id = await self.create_appointment(appointment_data, is_new_account=is_new_account)
            if appt_id:
                result.success = True
                result.appointment_created = True
                result.appointment_id = appt_id
            else:
                result.error = "Failed to create appointment"
                result.error_category = "appointment"

        except Exception as exc:
            result.error = str(exc)
            logger.warning("process_appointment failed for code %s: %s", code, exc)

        return result
