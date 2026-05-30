from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import hash_password
from app.exceptions import NotFoundError, ValidationError
from app.utils.pagination import PageParams, PageResult


async def create_user(db: AsyncSession, username: str, password: str, email: str = None, role: str = "user", avatar: str = None) -> User:
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise ValidationError("用户名已存在")
    user = User(username=username, password_hash=hash_password(password), email=email, role=role, avatar=avatar)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("用户不存在")
    return user


async def list_users(db: AsyncSession, params: PageParams, keyword: str = None) -> PageResult:
    query = select(User)
    count_query = select(func.count()).select_from(User)
    if keyword:
        like_filter = or_(User.username.contains(keyword), User.email.contains(keyword))
        query = query.where(like_filter)
        count_query = count_query.where(like_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    result = await db.execute(query.order_by(User.id).offset(params.offset).limit(params.page_size))
    users = result.scalars().all()
    return PageResult.create(items=users, total=total, page=params.page, page_size=params.page_size)


async def update_user(db: AsyncSession, user_id: int, **kwargs) -> User:
    user = await get_user(db, user_id)
    for k, v in kwargs.items():
        if v is not None:
            setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


async def toggle_user_status(db: AsyncSession, user_id: int, status: bool) -> User:
    user = await get_user(db, user_id)
    user.status = status
    await db.commit()
    await db.refresh(user)
    return user


async def reset_password(db: AsyncSession, user_id: int, new_password: str) -> User:
    user = await get_user(db, user_id)
    user.password_hash = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: int):
    user = await get_user(db, user_id)
    await db.delete(user)
    await db.commit()
