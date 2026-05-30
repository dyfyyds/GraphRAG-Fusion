from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    conversation_id: int | None = None


class ChatSSEChunk(BaseModel):
    event: str  # answer / sources / done / error
    data: str


class SourceItem(BaseModel):
    document_name: str
    page_number: int | None = None
    chunk_content: str
    score: float
