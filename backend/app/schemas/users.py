from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = None
    role: str = "user"
    avatar: str | None = None


class UserUpdate(BaseModel):
    email: str | None = None
    role: str | None = None
    status: bool | None = None
    avatar: str | None = None


class UserStatusToggle(BaseModel):
    status: bool


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class UserListQuery(BaseModel):
    page: int = 1
    page_size: int = 20
    keyword: str | None = None
