from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.exceptions import register_exception_handlers, AuthError


def setup_exception_handlers(app):
    register_exception_handlers(app)

    # Override validation error handler to provide better error messages
    async def improved_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Check if this is a login request with missing/invalid fields
        errors = exc.errors()
        error_messages = []
        for error in errors:
            loc = error.get("loc", [])
            msg = error.get("msg", "")
            if len(loc) > 1 and loc[1] in ("username", "password"):
                if "field required" in msg.lower():
                    error_messages.append(f"请填写{loc[1]}")
                elif "ensure this value" in msg.lower():
                    error_messages.append(f"{loc[1]}格式不正确")

        if error_messages:
            return JSONResponse(
                status_code=422,
                content={"code": "VALIDATION_ERROR", "message": "、".join(error_messages)},
            )

        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "参数校验失败", "detail": errors},
        )

    # Remove existing validation error handler and add improved one
    existing_handler = app.exception_handlers.get(RequestValidationError)
    if existing_handler and hasattr(existing_handler, '__name__') and existing_handler.__name__ == 'validation_error_handler':
        del app.exception_handlers[RequestValidationError]

    app.add_exception_handler(RequestValidationError, improved_validation_error_handler)
