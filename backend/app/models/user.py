from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # admin / user
    status: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # True=enabled
    avatar: Mapped[str | None] = mapped_column(Text, nullable=True)  # base64 or URL
