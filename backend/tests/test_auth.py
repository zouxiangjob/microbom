"""
认证服务纯函数单测：bcrypt 哈希校验与 JWT 签发/解析。
"""
import uuid

import jwt
import pytest

from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


def test_hash_and_verify_roundtrip():
    hashed = hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("right-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_malformed_hash_returns_false():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "admin")
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"


def test_token_has_expiry():
    token = create_access_token(uuid.uuid4(), "engineer")
    payload = decode_token(token)
    assert "exp" in payload


def test_decode_invalid_token_raises():
    with pytest.raises(jwt.PyJWTError):
        decode_token("garbage.token.value")
