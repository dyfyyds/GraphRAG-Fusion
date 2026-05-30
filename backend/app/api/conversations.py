from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import get_current_user, require_admin
from app.schemas.conversations import (
    ConversationOut, ConversationListResponse, MessageOut,
    AdminConversationOut, AdminConversationListResponse,
)
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["对话"])


class FeedbackRequest(BaseModel):
    value: str  # "positive" or "negative"


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.list_conversations_paginated(db, int(user["sub"]), page=page, page_size=size)


@router.get("/admin", response_model=AdminConversationListResponse)
async def admin_list_conversations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = None,
    user_id: int | None = None,
    feedback: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await conversation_service.admin_list_conversations(
        db, page=page, page_size=size, keyword=keyword,
        user_id=user_id, feedback=feedback, date_from=date_from, date_to=date_to,
    )


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages(conv_id: int, db: AsyncSession = Depends(get_db)):
    return await conversation_service.get_messages(db, conv_id)


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: int, db: AsyncSession = Depends(get_db)):
    await conversation_service.delete_conversation(db, conv_id)
    return {"message": "对话已删除"}


# Message feedback endpoint (mounted at /api/messages/{id}/feedback via main.py)
feedback_router = APIRouter(prefix="/api/messages", tags=["消息"])


@feedback_router.post("/{message_id}/feedback")
async def set_feedback(message_id: int, body: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update
    from app.models.message import Message
    value = body.value if body.value in ("positive", "negative") else None
    await db.execute(update(Message).where(Message.id == message_id).values(feedback=value))
    await db.commit()
    return {"message": "反馈已记录"}
