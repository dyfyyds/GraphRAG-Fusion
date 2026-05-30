from pydantic import BaseModel
from datetime import datetime


class ConversationOut(BaseModel):
    id: int
    user_id: int
    title: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: list[ConversationOut]
    total: int
    page: int
    page_size: int
    pages: int


class AdminConversationOut(BaseModel):
    id: int
    user_id: int
    username: str = ""
    title: str
    question: str = ""
    answer: str = ""
    sources: dict | None = None
    feedback: int | None = 0
    created_at: datetime

    class Config:
        from_attributes = True


class AdminConversationListResponse(BaseModel):
    items: list[AdminConversationOut]
    total: int
    page: int
    page_size: int
    pages: int


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: dict | None = None
    feedback: int | None = 0
    created_at: datetime

    class Config:
        from_attributes = True
