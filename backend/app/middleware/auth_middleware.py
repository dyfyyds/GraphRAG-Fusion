from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.utils.security import decode_jwt

EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/health",
    "/docs",
    "/openapi.json",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"code": "AUTH_ERROR", "message": "缺少认证令牌"})

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_jwt(token)
            request.state.user = payload
        except Exception:
            return JSONResponse(status_code=401, content={"code": "AUTH_ERROR", "message": "令牌无效或已过期"})

        return await call_next(request)
