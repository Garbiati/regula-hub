from regulahub.utils.crypto import hash_password


def test_hash_password_uppercases_before_hashing():
    # "102030" uppercased is still "102030"
    result = hash_password("102030")
    assert len(result) == 64
    assert result == hash_password("102030")


def test_hash_password_case_insensitive():
    # "PortalTM" and "portaltm" should produce same hash (both uppercased first)
    assert hash_password("PortalTM") == hash_password("portaltm")
    assert hash_password("PortalTM") == hash_password("PORTALTM")


def test_hash_password_known_value():
    # SHA-256 of "102030" (already uppercase)
    import hashlib

    expected = hashlib.sha256(b"102030").hexdigest()
    assert hash_password("102030") == expected
