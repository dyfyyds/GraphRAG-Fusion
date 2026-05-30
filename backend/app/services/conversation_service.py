from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.exceptions import NotFoundError
from app.utils.pagination import PageParams, PageResult


async def list_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id, Conversation.is_deleted == False)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def list_conversations_paginated(
    db: AsyncSession,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> PageResult:
    base_filter = and_(Conversation.user_id == user_id, Conversation.is_deleted == False)
    count_q = select(func.count()).select_from(Conversation).where(base_filter)
    total = (await db.execute(count_q)).scalar() or 0
    params = PageParams(page=page, page_size=page_size)
    result = await db.execute(
        select(Conversation)
        .where(base_filter)
        .order_by(Conversation.updated_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )
    items = list(result.scalars().all())
    return PageResult.create(items=items, total=total, page=page, page_size=page_size)


async def admin_list_conversations(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    user_id: int | None = None,
    feedback: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> PageResult:
    """Admin-level conversation list with messages (Q&A pairs), search and filters."""
    from sqlalchemy import cast, String

    # Base query: conversations joined with user
    base = (
        select(Conversation, User.username)
        .join(User, Conversation.user_id == User.id)
        .where(Conversation.is_deleted == False)
    )

    if user_id:
        base = base.where(Conversation.user_id == user_id)
    if date_from:
        base = base.where(cast(Conversation.created_at, String) >= date_from)
    if date_to:
        base = base.where(cast(Conversation.created_at, String) <= date_to)

    # If keyword or feedback filter is set, we need to join messages
    if keyword or feedback:
        # Subquery: first user message per conversation
        first_user_msg = (
            select(
                Message.conversation_id.label("conv_id"),
                Message.content.label("question"),
                Message.feedback.label("msg_feedback"),
                func.min(Message.id).label("min_id"),
            )
            .where(Message.role == "user")
            .group_by(Message.conversation_id, Message.content, Message.feedback)
            .subquery()
        )
        # Join to filter by keyword/feedback
        base = base.join(first_user_msg, Conversation.id == first_user_msg.c.conv_id)
        if keyword:
            base = base.where(first_user_msg.c.question.contains(keyword))
        if feedback == "positive":
            base = base.where(first_user_msg.c.msg_feedback == "1")
        elif feedback == "negative":
            base = base.where(first_user_msg.c.msg_feedback == "-1")
        elif feedback == "none":
            base = base.where((first_user_msg.c.msg_feedback == None) | (first_user_msg.c.msg_feedback == "0"))

    # Count
    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Fetch page
    params = PageParams(page=page, page_size=page_size)
    result = await db.execute(
        base.order_by(Conversation.created_at.desc())
        .offset(params.offset)
        .limit(params.page_size)
    )

    items = []
    for row in result.all():
        conv = row[0]
        username = row[1] or ""
        # Fetch first user and assistant messages for this conversation
        user_msg = await db.execute(
            select(Message.content, Message.feedback)
            .where(Message.conversation_id == conv.id, Message.role == "user")
            .order_by(Message.id)
            .limit(1)
        )
        user_row = user_msg.first()
        asst_msg = await db.execute(
            select(Message.content, Message.sources)
            .where(Message.conversation_id == conv.id, Message.role == "assistant")
            .order_by(Message.id)
            .limit(1)
        )
        asst_row = asst_msg.first()
        items.append({
            "id": conv.id,
            "user_id": conv.user_id,
            "username": username,
            "title": conv.title,
            "question": user_row[0] if user_row else "",
            "answer": asst_row[0] if asst_row else "",
            "sources": asst_row[1] if asst_row else None,
            "feedback": user_row[1] if user_row else None,
            "created_at": conv.created_at,
        })

    return PageResult.create(items=items, total=total, page=page, page_size=page_size)


async def get_messages(db: AsyncSession, conversation_id: int) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def delete_conversation(db: AsyncSession, conversation_id: int):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise NotFoundError("对话不存在")
    conv.is_deleted = True
    await db.commit()
