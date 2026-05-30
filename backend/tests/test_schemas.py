"""Schema 校验测试"""
import pytest
from pydantic import ValidationError
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.schemas.chat import ChatRequest
from app.schemas.users import UserCreate


def test_login_request_valid():
    req = LoginRequest(username="admin", password="123456")
    assert req.username == "admin"
    assert req.password == "123456"


def test_login_request_empty_username():
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="123456")


def test_login_request_long_username():
    with pytest.raises(ValidationError):
        LoginRequest(username="a" * 51, password="123456")


def test_chat_request_valid():
    req = ChatRequest(question="什么是RAG？")
    assert req.question == "什么是RAG？"
    assert req.conversation_id is None


def test_chat_request_too_long():
    with pytest.raises(ValidationError):
        ChatRequest(question="a" * 4001)


def test_chat_request_empty():
    with pytest.raises(ValidationError):
        ChatRequest(question="")


def test_user_create_valid():
    user = UserCreate(username="test", password="123456")
    assert user.role == "user"


def test_user_create_short_password():
    with pytest.raises(ValidationError):
        UserCreate(username="test", password="12345")


def test_token_response():
    resp = TokenResponse(access_token="abc123")
    assert resp.token_type == "bearer"


def test_user_out():
    user = UserOut(id=1, username="admin", role="admin", status=True)
    assert user.email is None
