from regulahub.utils.masking import mask_username


def test_mask_username_returns_hex_hash():
    result = mask_username("operator_user")
    assert len(result) == 8
    assert all(c in "0123456789abcdef" for c in result)


def test_mask_username_is_deterministic():
    assert mask_username("user1") == mask_username("user1")


def test_mask_username_different_inputs_differ():
    assert mask_username("user1") != mask_username("user2")


def test_mask_username_hides_original():
    username = "real_operator_name"
    masked = mask_username(username)
    assert username not in masked
