"""安全工具测试 — bcrypt + JWT"""
from app.utils.security import hash_password, verify_password, create_jwt, decode_jwt


def test_hash_password():
    hashed = hash_password("test123")
    assert hashed != "test123"
    assert len(hashed) > 0


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_jwt():
    token = create_jwt({"sub": "1", "role": "user"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_jwt():
    payload = {"sub": "42", "role": "admin"}
    token = create_jwt(payload)
    decoded = decode_jwt(token)
    assert decoded["sub"] == "42"
    assert decoded["role"] == "admin"


def test_jwt_expiry():
    from datetime import timedelta
    token = create_jwt({"sub": "1"}, expires_delta=timedelta(seconds=1))
    decoded = decode_jwt(token)
    assert decoded["sub"] == "1"
