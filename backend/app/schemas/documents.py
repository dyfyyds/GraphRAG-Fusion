from pydantic import BaseModel
from datetime import datetime


class DocumentOut(BaseModel):
    id: int
    name: str
    file_path: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentStatsOut(BaseModel):
    total: int = 0
    completed: int = 0
    parsing: int = 0
    building_graph: int = 0
    graph_failed: int = 0
    pending: int = 0
    failed: int = 0


class ChunkOut(BaseModel):
    id: int
    document_id: int
    content: str
    chunk_index: int
    page_number: int | None = None
    vector_id: str | None = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    document_id: int
    name: str
    status: str
    message: str
