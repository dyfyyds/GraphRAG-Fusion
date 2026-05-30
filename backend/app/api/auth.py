from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import get_current_user
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, body.username, body.password)


@router.post("/logout")
async def logout():
    return {"message": "已登出"}


@router.get("/me", response_model=UserOut)
async def get_me(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await auth_service.get_current_user(db, int(user["sub"]))


@router.put("/password")
async def change_password(
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(db, int(user["sub"]), body["old_password"], body["new_password"])
    return {"message": "密码修改成功"}
