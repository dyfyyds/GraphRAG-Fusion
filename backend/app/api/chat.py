from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import get_current_user
from app.schemas.chat import ChatRequest
from app.services import chat_service

router = APIRouter(prefix="/api/chat", tags=["问答"])


@router.post("")
async def chat(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async def event_generator():
        try:
            async for line in chat_service.chat_stream(db, int(user["sub"]), body.question, body.conversation_id):
                yield f"data: {line}\n\n"
        except Exception as exc:
            yield chat_service.format_sse_event("error", f"问答服务异常：{str(exc)}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
