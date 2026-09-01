import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    generate_api_key,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="user-123", organization_id="org-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["org_id"] == "org-456"
    assert payload["type"] == "access"


def test_decode_token_rejects_tampered_signature():
    token = create_access_token(subject="user-123")
    tampered = token[:-4] + "abcd"
    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)


def test_opaque_token_hash_is_deterministic():
    token = generate_opaque_token()
    assert hash_opaque_token(token) == hash_opaque_token(token)
    assert hash_opaque_token(token) != token


def test_generate_api_key_shape():
    raw_key, key_prefix, key_hash = generate_api_key()
    assert raw_key.startswith("rf_live_")
    assert raw_key.startswith(key_prefix)
    assert key_hash == hash_opaque_token(raw_key)
