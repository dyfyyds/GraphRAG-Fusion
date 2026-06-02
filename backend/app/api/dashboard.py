from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.schemas.dashboard import DashboardOverview, StatsOut, TrendItem, HotQuestion, DocTypeItem, SystemHealthItem
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["工作台"])


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_overview(db)


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_stats(db)


@router.get("/trend", response_model=list[TrendItem])
async def get_trend(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_trend(db)


@router.get("/hot-questions", response_model=list[HotQuestion])
async def get_hot_questions(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_hot_questions(db)


@router.get("/doc-types", response_model=list[DocTypeItem])
async def get_doc_types(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_doc_types(db)


@router.get("/system-health", response_model=list[SystemHealthItem])
async def get_system_health():
    return await dashboard_service.get_system_health()
