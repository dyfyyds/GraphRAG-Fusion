from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import require_admin
from app.schemas.users import UserCreate, UserUpdate, UserStatusToggle, UserResetPassword, UserListQuery
from app.schemas.auth import UserOut
from app.services import user_service
from app.utils.pagination import PageParams

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = None,
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    params = PageParams(page=page, page_size=page_size)
    result = await user_service.list_users(db, params, keyword)
    return {"items": [UserOut.model_validate(u) for u in result.items], "total": result.total, "page": result.page, "page_size": result.page_size, "pages": result.pages}


@router.post("", response_model=UserOut)
async def create_user(body: UserCreate, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await user_service.create_user(db, body.username, body.password, body.email, body.role, body.avatar)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await user_service.update_user(db, user_id, **body.model_dump(exclude_unset=True))


@router.put("/{user_id}/status", response_model=UserOut)
async def toggle_user_status(user_id: int, body: UserStatusToggle, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await user_service.toggle_user_status(db, user_id, body.status)


@router.put("/{user_id}/reset-password")
async def reset_password(user_id: int, body: UserResetPassword, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await user_service.reset_password(db, user_id, body.new_password)
    return {"message": "密码已重置"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, _admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await user_service.delete_user(db, user_id)
    return {"message": "用户已删除"}
