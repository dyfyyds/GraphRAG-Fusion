from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import hash_password, verify_password, create_jwt, decode_jwt
from app.exceptions import AuthError


async def login(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("用户名或密码错误")
    if not user.status:
        raise AuthError("账号已被禁用")
    token = create_jwt({"sub": str(user.id), "username": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthError("用户不存在")
    return user


async def change_password(db: AsyncSession, user_id: int, old_password: str, new_password: str):
    user = await get_current_user(db, user_id)
    if not verify_password(old_password, user.password_hash):
        raise AuthError("原密码错误")
    user.password_hash = hash_password(new_password)
    await db.commit()
