"""Generic HTTP client for pushing enriched appointments to integration systems.

Replicates the ptm-regulation-service flow:
find_patient → register/update_patient → list_doctors → find_reminder → create_reminder
"""

import dataclasses
import logging

import httpx

from regulahub.db.models import System, SystemEndpoint

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class PushResult:
    """Result of pushing a single appointment to the integration system."""

    code: str
    success: bool
    patient_created: bool = False
    patient_updated: bool = False
    reminder_created: bool = False
    reminder_skipped: bool = False
    error: str | None = None


@dataclasses.dataclass
class BatchPushResult:
    """Aggregated result of pushing a batch of appointments."""

    total: int = 0
    pushed: int = 0
    failed: int = 0
    results: list[PushResult] = dataclasses.field(default_factory=list)


class IntegrationPushClient:
    """HTTP client that pushes enriched appointment data to an integration system.

    Reads endpoint configuration from the database (system_endpoints table) and
    constructs HTTP requests dynamically.
    """

    def __init__(
        self,
        system: System,
        endpoints: list[SystemEndpoint],
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = (system.base_url or "").rstrip("/")
        self._endpoints = {ep.name: ep for ep in endpoints}
        self._api_key = api_key
        self._timeout = timeout
        self._doctors_cache: list[dict] | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "IntegrationPushClient":
        headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        self._client = httpx.AsyncClient(timeout=self._timeout, headers=headers)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_url(self, endpoint_name: str, path_params: dict | None = None) -> str:
        """Build full URL from endpoint config."""
        ep = self._endpoints.get(endpoint_name)
        if not ep:
            raise ValueError(f"Endpoint '{endpoint_name}' not configured")
        base = (ep.base_url_override or self._base_url).rstrip("/")
        path = ep.path
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))
        return f"{base}{path}"

    async def _request(
        self,
        endpoint_name: str,
        *,
        path_params: dict | None = None,
        query_params: dict | None = None,
        json_body: dict | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request using endpoint configuration."""
        if not self._client:
            raise RuntimeError("Client not initialized — use async context manager")
        ep = self._endpoints.get(endpoint_name)
        if not ep:
            raise ValueError(f"Endpoint '{endpoint_name}' not configured")
        url = self._build_url(endpoint_name, path_params)
        method = (ep.http_method or "GET").upper()
        return await self._client.request(method, url, params=query_params, json=json_body)

    async def find_patient(self, cns: str) -> dict | None:
        """Search for a patient by CNS. Returns patient dict or None."""
        try:
            resp = await self._request("find_patient", query_params={"cns": cns})
            if resp.status_code == 200:
                data = resp.json()
                # Handle both list and single-object responses
                if isinstance(data, list):
                    return data[0] if data else None
                return data if data.get("id") else None
            return None
        except Exception:
            logger.warning("find_patient failed for CNS (masked)")
            return None

    async def register_patient(self, patient_data: dict) -> dict | None:
        """Register a new patient. Returns created patient dict or None."""
        try:
            resp = await self._request("register_patient", json_body=patient_data)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning("register_patient failed: %s", resp.status_code)
            return None
        except Exception:
            logger.warning("register_patient request failed")
            return None

    async def update_patient(self, patient_id: str, patient_data: dict) -> dict | None:
        """Update an existing patient. Returns updated patient dict or None."""
        try:
            resp = await self._request("update_patient", path_params={"id": patient_id}, json_body=patient_data)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("update_patient failed: %s", resp.status_code)
            return None
        except Exception:
            logger.warning("update_patient request failed")
            return None

    async def list_doctors(self) -> list[dict]:
        """List doctors from the integration system. Cached per execution."""
        if self._doctors_cache is not None:
            return self._doctors_cache
        try:
            resp = await self._request("list_doctors")
            if resp.status_code == 200:
                data = resp.json()
                self._doctors_cache = data if isinstance(data, list) else data.get("items", [])
                return self._doctors_cache
            self._doctors_cache = []
            return self._doctors_cache
        except Exception:
            logger.warning("list_doctors request failed")
            self._doctors_cache = []
            return self._doctors_cache

    async def find_reminder(self, patient_id: str, appointment_date: str) -> dict | None:
        """Check if a reminder already exists for this patient and date."""
        try:
            resp = await self._request(
                "find_reminder",
                query_params={"patient": patient_id, "date": appointment_date},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data[0] if data else None
                return data if data.get("id") else None
            return None
        except Exception:
            logger.warning("find_reminder request failed")
            return None

    async def create_reminder(self, reminder_data: dict) -> dict | None:
        """Create a new reminder. Returns created reminder dict or None."""
        try:
            resp = await self._request("create_reminder", json_body=reminder_data)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.warning("create_reminder failed: %s", resp.status_code)
            return None
        except Exception:
            logger.warning("create_reminder request failed")
            return None

    async def process_appointment(self, enriched: dict) -> PushResult:
        """Execute the full integration flow for a single enriched appointment.

        Flow: find_patient → register/update → list_doctors → find_reminder → create_reminder
        """
        code = enriched.get("code", "unknown")
        result = PushResult(code=code, success=False)

        try:
            cns = enriched.get("patient_cns", "")
            if not cns:
                result.error = "Missing patient CNS"
                return result

            # Step 1: Find or register patient
            patient = await self.find_patient(cns)
            patient_data = self._build_patient_payload(enriched)

            if patient:
                patient_id = str(patient.get("id", ""))
                # Update patient with latest data
                updated = await self.update_patient(patient_id, patient_data)
                if updated:
                    result.patient_updated = True
            else:
                patient = await self.register_patient(patient_data)
                if not patient:
                    result.error = "Failed to register patient"
                    return result
                patient_id = str(patient.get("id", ""))
                result.patient_created = True

            # Step 2: Resolve doctor (cached)
            doctor_name = enriched.get("doctor_name", "")
            doctor_id = await self._resolve_doctor_id(doctor_name)

            # Step 3: Check for existing reminder (idempotency)
            appointment_date = enriched.get("appointment_date", "")
            existing_reminder = await self.find_reminder(patient_id, appointment_date)
            if existing_reminder:
                result.success = True
                result.reminder_skipped = True
                return result

            # Step 4: Create reminder
            reminder_data = self._build_reminder_payload(enriched, patient_id, doctor_id)
            reminder = await self.create_reminder(reminder_data)
            if reminder:
                result.success = True
                result.reminder_created = True
            else:
                result.error = "Failed to create reminder"

        except Exception as exc:
            result.error = str(exc)
            logger.warning("process_appointment failed for code %s: %s", code, exc)

        return result

    async def _resolve_doctor_id(self, doctor_name: str) -> str | None:
        """Resolve doctor ID by name from cached doctor list."""
        if not doctor_name:
            return None
        doctors = await self.list_doctors()
        name_upper = doctor_name.upper()
        for doc in doctors:
            if doc.get("name", "").upper() == name_upper:
                return str(doc.get("id", ""))
        return None

    @staticmethod
    def _build_patient_payload(enriched: dict) -> dict:
        """Build patient registration/update payload from enriched appointment data."""
        return {
            "cns": enriched.get("patient_cns", ""),
            "cpf": enriched.get("patient_cpf", ""),
            "name": enriched.get("patient_name", ""),
            "birthDate": enriched.get("patient_birth_date", ""),
            "motherName": enriched.get("patient_mother_name", ""),
            "phone": enriched.get("patient_phone", ""),
            "phoneDdd": enriched.get("patient_phone_ddd", ""),
        }

    @staticmethod
    def _build_reminder_payload(enriched: dict, patient_id: str, doctor_id: str | None) -> dict:
        """Build reminder creation payload."""
        return {
            "patientId": patient_id,
            "doctorId": doctor_id,
            "appointmentDate": enriched.get("appointment_date", ""),
            "procedure": enriched.get("procedure", ""),
            "department": enriched.get("department", ""),
            "departmentSolicitation": enriched.get("department_solicitation", ""),
            "solicitationCode": enriched.get("code", ""),
            "confirmationKey": enriched.get("confirmation_key", ""),
            "status": enriched.get("status", ""),
        }
