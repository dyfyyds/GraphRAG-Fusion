import json
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rag_engine import get_rag_engine
from app.models.message import Message
from app.models.conversation import Conversation
from app.exceptions import ValidationError


INJECTION_PATTERNS = [
    # English patterns
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+",
    r"system\s*:\s*",
    r"<\|system\|>",
    r"jailbreak",
    r"do\s+anything\s+now",
    r"dan\s+mode",
    # Chinese patterns
    r"忽略.{0,10}(之前|以上|所有).{0,10}(指令|提示|规则)",
    r"你现在是",
    r"进入.{0,5}(开发者|调试|越狱|无限制).{0,5}模式",
    r"无视.{0,10}(安全|限制|规则|约束)",
    r"扮演.{0,10}(角色|助手|AI)",
    r"输出.{0,10}(系统|原始|初始).{0,10}(提示|prompt)",
]


def format_sse_event(event: str, data) -> str:
    return f"data: {json.dumps({'event': event, 'data': data}, ensure_ascii=False)}\n\n"


def detect_injection(text: str) -> bool:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


async def chat_stream(db: AsyncSession, user_id: int, question: str, conversation_id: int = None) -> AsyncGenerator[str, None]:
    if detect_injection(question):
        yield json.dumps({"event": "error", "data": "检测到不安全的输入"}, ensure_ascii=False) + "\n"
        return

    # 获取或创建对话
    if conversation_id:
        result = await db.get(Conversation, conversation_id)
        if not result:
            yield json.dumps({"event": "error", "data": "对话不存在"}, ensure_ascii=False) + "\n"
            return
        conv = result
    else:
        conv = Conversation(user_id=user_id, title=question[:50])
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # 保存用户消息
    user_msg = Message(conversation_id=conv.id, role="user", content=question)
    db.add(user_msg)
    await db.commit()

    # RAG 检索 + 流式生成
    engine = get_rag_engine()
    full_answer = ""
    sources = []

    try:
        async for event_type, data in engine.query(question):
            if event_type == "sources":
                sources = data
                yield json.dumps({"event": "sources", "data": json.dumps(data, ensure_ascii=False)}, ensure_ascii=False) + "\n"
            elif event_type == "answer":
                if data:
                    full_answer += data
                    yield json.dumps({"event": "answer", "data": data}, ensure_ascii=False) + "\n"
            elif event_type == "error":
                yield json.dumps({"event": "error", "data": data}, ensure_ascii=False) + "\n"
                return
    except Exception as exc:
        yield json.dumps({"event": "error", "data": f"问答失败：{str(exc)}"}, ensure_ascii=False) + "\n"
        return

    # 保存助手消息
    assistant_msg = Message(
        conversation_id=conv.id, role="assistant", content=full_answer, sources={"items": sources}
    )
    db.add(assistant_msg)
    await db.commit()

    yield json.dumps({"event": "done", "data": json.dumps({"conversation_id": conv.id})}, ensure_ascii=False) + "\n"


async def submit_feedback(db: AsyncSession, message_id: int, feedback: int):
    msg = await db.get(Message, message_id)
    if msg:
        msg.feedback = feedback
        await db.commit()
