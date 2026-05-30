"""异常处理测试"""
from app.exceptions import AppError, AuthError, NotFoundError, PermissionError, ValidationError


def test_app_error_default():
    err = AppError()
    assert err.message == "服务器内部错误"
    assert err.code == "APP_ERROR"
    assert err.status_code == 500


def test_auth_error():
    err = AuthError("token过期")
    assert err.message == "token过期"
    assert err.code == "AUTH_ERROR"
    assert err.status_code == 401


def test_not_found_error():
    err = NotFoundError("文档不存在")
    assert err.status_code == 404
    assert err.code == "NOT_FOUND"


def test_permission_error():
    err = PermissionError()
    assert err.status_code == 403


def test_validation_error():
    err = ValidationError("参数错误")
    assert err.status_code == 422
    assert err.code == "VALIDATION_ERROR"


def test_error_inheritance():
    assert issubclass(AuthError, AppError)
    assert issubclass(NotFoundError, AppError)
    assert issubclass(PermissionError, AppError)
    assert issubclass(ValidationError, AppError)
