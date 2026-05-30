from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.exceptions import PermissionError, AuthError


async def get_current_user(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not user:
        raise AuthError("未认证")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise PermissionError("需要管理员权限")
    return user
