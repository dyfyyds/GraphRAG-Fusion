from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IDMixin


class Chunk(Base, IDMixin):
    __tablename__ = "chunks"

    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ChromaDB 中的 ID
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
