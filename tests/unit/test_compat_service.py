"""Tests for the Absens-compatible service layer."""

import asyncio
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from regulahub.api.controllers.compat.absens_schemas import AbsensAppointmentResponse, AbsensDetailResponse
from regulahub.services.compat_service import (
    EnrichmentData,
    _enrich_listings,
    _fetch_details_for_codes,
    _resolve_all_credentials,
    fetch_appointments,
    fetch_detail,
    format_appointment_date,
    map_detail_to_absens,
    map_listing_to_absens,
)
from regulahub.services.credential_service import CredentialNotFoundError
from regulahub.sisreg.client import SisregLoginError
from regulahub.sisreg.models import AppointmentDetail, AppointmentListing, BestPhone, CadwebPatientData


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch):
    """Provide a valid Fernet key for all tests."""
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", key)
    from regulahub.config import get_credential_encryption_settings
    from regulahub.utils.encryption import _get_fernet

    get_credential_encryption_settings.cache_clear()
    _get_fernet.cache_clear()


# ─── format_appointment_date ────────────────────────────────────────────────


class TestFormatAppointmentDate:
    def test_none_returns_empty(self):
        """T1: None → empty string."""
        assert format_appointment_date(None) == ""

    def test_empty_returns_empty(self):
        """T2: Empty string → empty string."""
        assert format_appointment_date("") == ""

    def test_passthrough_when_contains_bullet(self):
        """T3: Already formatted → passthrough."""
        value = "QUA ● 23/04/2025 ● 13h00min"
        assert format_appointment_date(value) == value

    def test_date_only_adds_weekday_and_midnight(self):
        """T4: dd/MM/yyyy → 'DIA ● dd/MM/yyyy ● 00h00min'."""
        # 20/03/2026 is a Friday
        result = format_appointment_date("20/03/2026")
        assert result == "SEX ● 20/03/2026 ● 00h00min"

    def test_date_with_time(self):
        """T5: dd/MM/yyyy HH:mm → 'DIA ● dd/MM/yyyy ● HHhMMmin'."""
        result = format_appointment_date("20/03/2026 14:30")
        assert result == "SEX ● 20/03/2026 ● 14h30min"

    def test_whitespace_only_returns_empty(self):
        """T5b: Whitespace-only input → empty string."""
        assert format_appointment_date("   ") == ""

    def test_invalid_date_returns_empty(self):
        """T5c: Invalid date like '32/13/2026' → empty string."""
        assert format_appointment_date("32/13/2026") == ""

    def test_invalid_time_falls_back_to_midnight(self):
        """T5d: Valid date with invalid time '25:99' → fallback to 00h00min."""
        result = format_appointment_date("20/03/2026 25:99")
        assert result == "SEX ● 20/03/2026 ● 00h00min"


# ─── map_listing_to_absens ──────────────────────────────────────────────────


class TestMapListingToAbsens:
    def test_full_listing_with_enrichment(self):
        """T6: Complete listing with enrichment maps all fields correctly."""
        listing = AppointmentListing(
            code="12345",
            request_date="18/03/2026",
            patient_name="JOHN DOE",
            dept_execute="HOSPITAL REGIONAL",
            dept_solicitation="UBS CENTRO",
            procedure="TELECONSULTA EM CARDIOLOGIA",
            status="AGE/PEN/EXEC",
        )
        enrichment = EnrichmentData(
            detail=AppointmentDetail(patient_birth_date="15/04/1990"),
            cadweb=CadwebPatientData(mother_name="MARIA DA SILVA"),
        )
        result = map_listing_to_absens(listing, enrichment=enrichment)
        assert isinstance(result, AbsensAppointmentResponse)

        data = result.model_dump(by_alias=True)
        assert data["cod"] == "12345"
        assert data["departmentExecute"] == "HOSPITAL REGIONAL"
        assert data["departmentSolicitation"] == "UBS CENTRO"
        assert data["procedure"] == "TELECONSULTA EM CARDIOLOGIA"
        assert data["statusSisreg"] == "AGE/PEN/EXEC"
        assert data["patientBirthday"] == "15/04/1990"
        assert data["patientMotherName"] == "MARIA DA SILVA"

    def test_listing_without_cadweb(self):
        """Enrichment without CadWeb → mother_name stays empty."""
        listing = AppointmentListing(
            code="12345",
            request_date="18/03/2026",
            patient_name="JOHN DOE",
        )
        enrichment = EnrichmentData(
            detail=AppointmentDetail(patient_birth_date="15/04/1990"),
            cadweb=None,
        )
        result = map_listing_to_absens(listing, enrichment=enrichment)
        data = result.model_dump(by_alias=True)
        assert data["patientBirthday"] == "15/04/1990"
        assert data["patientMotherName"] == ""

    def test_empty_listing_defaults(self):
        """T7: Empty listing → required strings are '', nullable is None."""
        listing = AppointmentListing(code="", request_date="", patient_name="", status="")
        result = map_listing_to_absens(listing)

        data = result.model_dump(by_alias=True)
        assert data["cod"] == ""
        assert data["departmentExecute"] == ""
        assert data["departmentSolicitation"] == ""
        assert data["procedure"] == ""
        assert data["statusSisreg"] is None  # empty string becomes None
        assert data["patientBirthday"] == ""
        assert data["patientMotherName"] == ""


# ─── map_detail_to_absens ───────────────────────────────────────────────────


class TestMapDetailToAbsens:
    def test_full_detail(self):
        """T8: Complete detail maps all key fields including BC-1..5 fixes."""
        detail = AppointmentDetail(
            sol_code="12345",
            confirmation_key="CONF-ABC-123",
            patient_name="MARIA DA SILVA",
            patient_cns="898001234567890",
            appointment_date="20/03/2026 14:30",
            best_phone=BestPhone(raw="(92) 98765-4321", ddd="92", number="98765-4321"),
            department="HOSPITAL REGIONAL DE MANAUS",
            doctor_name="DR. JOAO SOUZA",
            req_unit_name="UBS CENTRO",
            req_unit_cnes="1234567",
            sol_status="AGE/PEN/EXEC",
        )
        result = map_detail_to_absens(detail, "12345")
        assert isinstance(result, AbsensDetailResponse)

        data = result.model_dump(by_alias=True)
        assert data["cod"] == "12345"
        assert data["confirmationKey"] == "CONF-ABC-123"
        assert data["patient"] == "MARIA DA SILVA"
        assert data["cns"] == "898001234567890"
        assert data["appointmentDate"] == "SEX ● 20/03/2026 ● 14h30min"
        assert data["bestPhone"] == {"ddd": "92", "number": "98765-4321"}
        assert data["patientPhones"] == [{"ddd": "92", "number": "98765-4321"}]
        assert data["departmentExecute"] == "HOSPITAL REGIONAL DE MANAUS"
        assert data["doctorExecute"] == "DR. JOAO SOUZA"
        assert data["departmentSolicitation"] == "UBS CENTRO"
        assert data["departmentSolicitationInfos"] == {"cnes": "1234567", "department": "UBS CENTRO"}
        assert data["statusSisreg"] == "AGE/PEN/EXEC"

    def test_detail_with_cadweb_cpf_and_phone(self):
        """CadWeb enrichment provides CPF and overrides phone."""
        detail = AppointmentDetail(
            sol_code="12345",
            patient_cns="898001234567890",
            best_phone=BestPhone(raw="(92) 3333-4444", ddd="92", number="3333-4444"),
        )
        cadweb = CadwebPatientData(
            cpf="33525528272",
            phone_type="CELULAR",
            phone_ddd="92",
            phone_number="99211-9712",
        )
        result = map_detail_to_absens(detail, "12345", cadweb=cadweb)
        data = result.model_dump(by_alias=True)

        assert data["patientCPF"] == "33525528272"
        assert data["bestPhone"] == {"ddd": "92", "number": "99211-9712"}
        assert data["patientPhones"] == [{"ddd": "92", "number": "99211-9712"}]

    def test_detail_cadweb_no_phone_falls_back(self):
        """CadWeb without phone → falls back to fichaAmbulatorial phone."""
        detail = AppointmentDetail(
            best_phone=BestPhone(raw="(92) 98765-4321", ddd="92", number="98765-4321"),
        )
        cadweb = CadwebPatientData(cpf="33525528272")
        result = map_detail_to_absens(detail, "123", cadweb=cadweb)
        data = result.model_dump(by_alias=True)

        assert data["patientCPF"] == "33525528272"
        assert data["bestPhone"] == {"ddd": "92", "number": "98765-4321"}

    def test_detail_with_none_optionals(self):
        """T9: All None optionals → required strings '', nullable None."""
        detail = AppointmentDetail()
        result = map_detail_to_absens(detail, "99999")

        data = result.model_dump(by_alias=True)
        assert data["cod"] == "99999"  # fallback to code param
        assert data["confirmationKey"] == ""
        assert data["patient"] == ""
        assert data["cns"] == ""
        assert data["appointmentDate"] == ""
        assert data["bestPhone"] is None
        assert data["patientPhones"] is None
        assert data["id"] is None
        assert data["patientCPF"] is None
        assert data["departmentExecute"] == ""
        assert data["doctorExecute"] == ""
        assert data["departmentSolicitation"] == ""
        assert data["departmentSolicitationInfos"] is None
        assert data["statusSisreg"] == ""

    def test_phone_mapping(self):
        """T10: BestPhone maps to PatientPhoneResponse."""
        detail = AppointmentDetail(
            best_phone=BestPhone(raw="(92) 98765-4321", ddd="92", number="98765-4321"),
        )
        result = map_detail_to_absens(detail, "123")

        data = result.model_dump(by_alias=True)
        assert data["bestPhone"]["ddd"] == "92"
        assert data["bestPhone"]["number"] == "98765-4321"

    def test_phone_none(self):
        """T11: best_phone=None → patientPhones=None, bestPhone=None."""
        detail = AppointmentDetail(best_phone=None)
        result = map_detail_to_absens(detail, "123")

        data = result.model_dump(by_alias=True)
        assert data["patientPhones"] is None
        assert data["bestPhone"] is None

    def test_dept_sol_infos_only_cnes(self):
        """BC-4: Only req_unit_cnes set → departmentSolicitationInfos populated."""
        detail = AppointmentDetail(req_unit_cnes="7654321")
        result = map_detail_to_absens(detail, "123")

        data = result.model_dump(by_alias=True)
        assert data["departmentSolicitationInfos"] == {"cnes": "7654321", "department": ""}

    def test_dept_sol_infos_only_name(self):
        """BC-4: Only req_unit_name set → departmentSolicitationInfos populated."""
        detail = AppointmentDetail(req_unit_name="UBS NORTE")
        result = map_detail_to_absens(detail, "123")

        data = result.model_dump(by_alias=True)
        assert data["departmentSolicitationInfos"] == {"cnes": "", "department": "UBS NORTE"}
        assert data["departmentSolicitation"] == "UBS NORTE"

    def test_dept_sol_infos_none_when_both_missing(self):
        """BC-4: Neither cnes nor name → departmentSolicitationInfos is None."""
        detail = AppointmentDetail()
        result = map_detail_to_absens(detail, "123")
        assert result.department_solicitation_infos is None


# ─── fetch_appointments ─────────────────────────────────────────────────────


def _make_cred(username="user1", encrypted_password=None):
    """Create a mock credential object."""
    from regulahub.utils.encryption import encrypt_password

    cred = types.SimpleNamespace()
    cred.username = username
    cred.encrypted_password = encrypted_password or encrypt_password("secret")
    return cred


def _make_listing(code: str = "100", **kwargs) -> AppointmentListing:
    return AppointmentListing(code=code, request_date="18/03/2026", patient_name="TEST", **kwargs)


_SVC_MODULE = "regulahub.services.compat_service"


class TestFetchAppointments:
    async def test_parallel_search_deduplicates(self):
        """T12: 2 credentials, overlapping results → deduplicated."""
        # Each operator returns 2 items, with code "102" duplicated
        listings_op1 = [_make_listing("101"), _make_listing("102")]
        listings_op2 = [_make_listing("102"), _make_listing("103")]

        call_count = 0

        async def mock_search(filters):
            nonlocal call_count
            result = MagicMock()
            result.items = listings_op1 if call_count == 0 else listings_op2
            call_count += 1
            return result

        mock_client = AsyncMock()
        mock_client.search = mock_search
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def mock_resolve(db_session):
            return [("op1", "secret"), ("op2", "secret")]

        async def mock_enrich(listings, credentials):
            return {}

        with (
            patch(f"{_SVC_MODULE}._resolve_all_credentials", side_effect=mock_resolve),
            patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client),
            patch(f"{_SVC_MODULE}._enrich_listings", side_effect=mock_enrich),
        ):
            results = await fetch_appointments("2026-03-18", AsyncMock())

        assert len(results) == 3
        codes = [r.cod for r in results]
        assert "101" in codes
        assert "102" in codes
        assert "103" in codes

    async def test_no_credentials_raises(self):
        """T13: No credentials → CredentialNotFoundError."""

        async def mock_resolve(db_session):
            raise CredentialNotFoundError("No VIDEOFONISTA credentials configured for SISREG")

        with (
            patch(f"{_SVC_MODULE}._resolve_all_credentials", side_effect=mock_resolve),
            pytest.raises(CredentialNotFoundError),
        ):
            await fetch_appointments("2026-03-18", AsyncMock())


class TestResolveAllCredentials:
    async def test_partial_decryption_failure(self):
        """T15b: 3 credentials, 2 fail decryption, 1 succeeds → returns 1 credential."""
        good_cred = _make_cred(username="good_user")
        bad_cred_1 = _make_cred(username="bad_user_1")
        bad_cred_1.encrypted_password = "invalid-encrypted-data"
        bad_cred_2 = _make_cred(username="bad_user_2")
        bad_cred_2.encrypted_password = "also-invalid"

        mock_repo = AsyncMock()
        mock_repo.get_active_by_system_and_profile = AsyncMock(return_value=[bad_cred_1, bad_cred_2, good_cred])

        with patch(f"{_SVC_MODULE}.CredentialRepository", return_value=mock_repo):
            result = await _resolve_all_credentials(AsyncMock())

        assert len(result) == 1
        assert result[0][0] == "good_user"

    async def test_all_decryption_fails_raises(self):
        """T15c: All credentials fail decryption → CredentialNotFoundError."""
        bad_cred = _make_cred(username="bad_user")
        bad_cred.encrypted_password = "invalid-encrypted-data"

        mock_repo = AsyncMock()
        mock_repo.get_active_by_system_and_profile = AsyncMock(return_value=[bad_cred])

        with (
            patch(f"{_SVC_MODULE}.CredentialRepository", return_value=mock_repo),
            pytest.raises(CredentialNotFoundError, match="All VIDEOFONISTA credentials failed decryption"),
        ):
            await _resolve_all_credentials(AsyncMock())


class TestFetchDetail:
    async def test_success(self):
        """T14: Successful detail fetch and mapping with CadWeb."""
        detail = AppointmentDetail(
            sol_code="12345",
            confirmation_key="CONF-123",
            patient_cns="898001234567890",
            appointment_date="20/03/2026",
        )
        cadweb = CadwebPatientData(cpf="33525528272", phone_ddd="92", phone_number="99211-9712")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(return_value=detail)
        mock_client.cadweb_lookup = AsyncMock(return_value=cadweb)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def mock_resolve(*args, **kwargs):
            return ("user1", "pass1")

        with (
            patch(f"{_SVC_MODULE}.resolve_single_credential", side_effect=mock_resolve),
            patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client),
        ):
            result = await fetch_detail("12345", AsyncMock())

        assert isinstance(result, AbsensDetailResponse)
        assert result.cod == "12345"
        assert result.cns == "898001234567890"
        data = result.model_dump(by_alias=True)
        assert data["patientCPF"] == "33525528272"
        assert data["bestPhone"] == {"ddd": "92", "number": "99211-9712"}

    async def test_cadweb_failure_graceful(self):
        """CadWeb failure → CPF=None, phone falls back to fichaAmbulatorial."""
        detail = AppointmentDetail(
            sol_code="12345",
            patient_cns="898001234567890",
            best_phone=BestPhone(raw="(92) 3333-4444", ddd="92", number="3333-4444"),
        )

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(return_value=detail)
        mock_client.cadweb_lookup = AsyncMock(side_effect=RuntimeError("CadWeb down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        async def mock_resolve(*args, **kwargs):
            return ("user1", "pass1")

        with (
            patch(f"{_SVC_MODULE}.resolve_single_credential", side_effect=mock_resolve),
            patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client),
        ):
            result = await fetch_detail("12345", AsyncMock())

        data = result.model_dump(by_alias=True)
        assert data["patientCPF"] is None
        assert data["bestPhone"] == {"ddd": "92", "number": "3333-4444"}

    async def test_no_credential_raises(self):
        """T15: No credential → CredentialNotFoundError."""

        async def mock_resolve(*args, **kwargs):
            raise CredentialNotFoundError("No credentials")

        with (
            patch(f"{_SVC_MODULE}.resolve_single_credential", side_effect=mock_resolve),
            pytest.raises(CredentialNotFoundError),
        ):
            await fetch_detail("12345", AsyncMock())


# ─── _fetch_details_for_codes ──────────────────────────────────────────────


class TestFetchDetailsForCodes:
    async def test_sequential_detail_and_cadweb_calls(self):
        """Detail + CadWeb called for each code within a single session."""
        details = {
            "101": AppointmentDetail(patient_birth_date="01/01/1990", patient_cns="CNS_A"),
            "102": AppointmentDetail(patient_birth_date="02/02/1985", patient_cns="CNS_B"),
        }
        cadweb_data = CadwebPatientData(cpf="33525528272", mother_name="MARIA")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(side_effect=lambda code: details[code])
        mock_client.cadweb_lookup = AsyncMock(return_value=cadweb_data)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        semaphore = asyncio.Semaphore(5)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _fetch_details_for_codes(["101", "102"], "user1", "pass1", semaphore)

        assert "101" in result
        assert "102" in result
        assert result["101"].detail.patient_birth_date == "01/01/1990"
        assert result["101"].cadweb.cpf == "33525528272"
        assert result["102"].detail.patient_birth_date == "02/02/1985"
        assert mock_client.detail.call_count == 2
        assert mock_client.cadweb_lookup.call_count == 2

    async def test_cadweb_cache_by_cns(self):
        """Same CNS in 2 codes → only 1 cadweb_lookup call."""
        details = {
            "101": AppointmentDetail(patient_birth_date="01/01/1990", patient_cns="CNS_SAME"),
            "102": AppointmentDetail(patient_birth_date="02/02/1985", patient_cns="CNS_SAME"),
        }
        cadweb_data = CadwebPatientData(cpf="33525528272")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(side_effect=lambda code: details[code])
        mock_client.cadweb_lookup = AsyncMock(return_value=cadweb_data)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        semaphore = asyncio.Semaphore(5)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _fetch_details_for_codes(["101", "102"], "user1", "pass1", semaphore)

        assert mock_client.cadweb_lookup.call_count == 1  # cached
        assert result["101"].cadweb.cpf == "33525528272"
        assert result["102"].cadweb.cpf == "33525528272"

    async def test_login_error_returns_empty(self):
        """SisregLoginError → empty dict (no enrichment data)."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=SisregLoginError("Login failed"))
        mock_client.__aexit__ = AsyncMock(return_value=False)

        semaphore = asyncio.Semaphore(5)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _fetch_details_for_codes(["101", "102"], "user1", "pass1", semaphore)

        assert result == {}

    async def test_individual_detail_failure(self):
        """One detail raises → that code is missing, rest succeed."""

        async def mock_detail(code):
            if code == "102":
                raise RuntimeError("SisReg timeout")
            return AppointmentDetail(patient_birth_date="01/01/1990")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(side_effect=mock_detail)
        mock_client.cadweb_lookup = AsyncMock(return_value=None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        semaphore = asyncio.Semaphore(5)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _fetch_details_for_codes(["101", "102", "103"], "user1", "pass1", semaphore)

        assert result["101"].detail.patient_birth_date == "01/01/1990"
        assert "102" not in result  # failed, not included
        assert result["103"].detail.patient_birth_date == "01/01/1990"

    async def test_cadweb_failure_graceful(self):
        """CadWeb fails → detail still enriched, cadweb=None."""
        detail = AppointmentDetail(patient_birth_date="01/01/1990", patient_cns="CNS_A")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(return_value=detail)
        mock_client.cadweb_lookup = AsyncMock(side_effect=RuntimeError("CadWeb timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        semaphore = asyncio.Semaphore(5)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _fetch_details_for_codes(["101"], "user1", "pass1", semaphore)

        assert result["101"].detail.patient_birth_date == "01/01/1990"
        assert result["101"].cadweb is None


# ─── _enrich_listings ──────────────────────────────────────────────────────


class TestEnrichListings:
    async def test_empty_listings_returns_empty_dict(self):
        """No listings → empty dict."""
        result = await _enrich_listings([], [("user1", "pass1")])
        assert result == {}

    async def test_single_credential_enriches_all_codes(self):
        """1 credential, 3 codes → all enriched with EnrichmentData."""
        listings = [_make_listing("101"), _make_listing("102"), _make_listing("103")]
        details = {
            "101": AppointmentDetail(patient_birth_date="01/01/1990"),
            "102": AppointmentDetail(patient_birth_date="02/02/1985"),
            "103": AppointmentDetail(patient_birth_date="03/03/1978"),
        }

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(side_effect=lambda code: details[code])
        mock_client.cadweb_lookup = AsyncMock(return_value=None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _enrich_listings(listings, [("user1", "pass1")])

        assert result["101"].detail.patient_birth_date == "01/01/1990"
        assert result["102"].detail.patient_birth_date == "02/02/1985"
        assert result["103"].detail.patient_birth_date == "03/03/1978"

    async def test_round_robin_distribution(self):
        """2 credentials, 4 codes → cred0 gets [0,2], cred1 gets [1,3]."""
        listings = [_make_listing("101"), _make_listing("102"), _make_listing("103"), _make_listing("104")]

        batches_seen: dict[str, list[str]] = {}

        async def track_fetch(codes, username, password, semaphore):
            batches_seen[username] = codes
            return {code: EnrichmentData(detail=AppointmentDetail(patient_birth_date="01/01/1990")) for code in codes}

        with patch(f"{_SVC_MODULE}._fetch_details_for_codes", side_effect=track_fetch):
            result = await _enrich_listings(listings, [("op1", "p1"), ("op2", "p2")])

        assert batches_seen["op1"] == ["101", "103"]
        assert batches_seen["op2"] == ["102", "104"]
        assert len(result) == 4

    async def test_login_failure_defaults_to_empty(self):
        """Credential fails login → no enrichment data for those codes."""
        listings = [_make_listing("101"), _make_listing("102")]

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=SisregLoginError("Login failed"))
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _enrich_listings(listings, [("user1", "pass1")])

        assert result == {}

    async def test_partial_detail_failure(self):
        """1 detail call fails → that code missing, others succeed."""

        async def mock_detail(code):
            if code == "102":
                raise RuntimeError("Timeout")
            return AppointmentDetail(patient_birth_date="15/04/1990")

        mock_client = AsyncMock()
        mock_client.detail = AsyncMock(side_effect=mock_detail)
        mock_client.cadweb_lookup = AsyncMock(return_value=None)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(f"{_SVC_MODULE}.SisregClient", return_value=mock_client):
            result = await _enrich_listings(
                [_make_listing("101"), _make_listing("102"), _make_listing("103")],
                [("user1", "pass1")],
            )

        assert result["101"].detail.patient_birth_date == "15/04/1990"
        assert "102" not in result
        assert result["103"].detail.patient_birth_date == "15/04/1990"
