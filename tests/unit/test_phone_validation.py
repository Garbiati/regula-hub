"""Tests for Brazilian phone validation in the integration worker."""

import pytest

from regulahub.services.integration_worker_service import _is_valid_brazilian_phone


class TestIsValidBrazilianPhone:
    """Test the phone validation function used during enrichment."""

    @pytest.mark.parametrize(
        "phone",
        [
            "11987654321",  # SP mobile
            "92991234567",  # AM mobile
            "2134567890",  # RJ landline
            "1133445566",  # SP landline
            "69992345678",  # RO mobile
            "99987654321",  # MA mobile (DDD 99)
        ],
    )
    def test_valid_phones(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is True

    @pytest.mark.parametrize(
        "phone",
        [
            "00000000000",
            "11111111111",
            "22222222222",
            "99999999999",
            "0000000000",
            "1111111111",
        ],
    )
    def test_all_same_digit_rejected(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is False

    @pytest.mark.parametrize(
        "phone",
        [
            "00987654321",  # DDD 00
            "01987654321",  # DDD 01
            "10987654321",  # DDD 10
        ],
    )
    def test_invalid_ddd_rejected(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is False

    @pytest.mark.parametrize(
        "phone",
        [
            "119876543",  # 9 digits
            "119876543210",  # 12 digits
            "1",
            "",
        ],
    )
    def test_wrong_length_rejected(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is False

    @pytest.mark.parametrize(
        "phone",
        [
            "11887654321",  # 11 digits, 3rd digit = 8
            "11787654321",  # 11 digits, 3rd digit = 7
        ],
    )
    def test_mobile_not_starting_with_9_rejected(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is False

    @pytest.mark.parametrize(
        "phone",
        [
            "1167890123",  # 10 digits, 3rd digit = 6
            "1197890123",  # 10 digits, 3rd digit = 9
        ],
    )
    def test_landline_invalid_prefix_rejected(self, phone: str) -> None:
        assert _is_valid_brazilian_phone(phone) is False
