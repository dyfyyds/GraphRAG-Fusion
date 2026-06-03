from pydantic import BaseModel
from datetime import date


class StatsOut(BaseModel):
    document_count: int = 0
    chunk_count: int = 0
    user_count: int = 0
    today_chat_count: int = 0


class TrendItem(BaseModel):
    date: date
    count: int


class HotQuestion(BaseModel):
    question: str
    count: int


class DocTypeItem(BaseModel):
    file_type: str
    count: int
    percentage: float


class SystemHealthItem(BaseModel):
    name: str
    status: str  # online / warning / offline
    detail: str = ""


class DashboardOverview(BaseModel):
    stats: StatsOut
    trend: list[TrendItem]
    hotQuestions: list[HotQuestion]
    docTypes: list[DocTypeItem]
