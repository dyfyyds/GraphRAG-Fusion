import os
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.dependencies import get_current_user
from app.schemas.documents import DocumentOut, DocumentListResponse, DocumentStatsOut, ChunkOut, UploadResponse
from app.services import document_service
from app.utils.file_utils import validate_file

router = APIRouter(prefix="/api/documents", tags=["知识库"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = None,
    file_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await document_service.list_documents(db, page=page, page_size=size, keyword=keyword, file_type=file_type, status=status)
    return result


@router.get("/stats", response_model=DocumentStatsOut)
async def get_document_stats(db: AsyncSession = Depends(get_db)):
    return await document_service.get_document_stats(db)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    content = await file.read()
    valid, msg = validate_file(file.filename, len(content))
    if not valid:
        return UploadResponse(document_id=0, name=file.filename, status="failed", message=msg)

    with open(file_path, "wb") as f:
        f.write(content)

    doc = await document_service.upload_document(db, file.filename, file_path, file.filename.rsplit(".", 1)[-1], len(content), int(user["sub"]))
    background_tasks.add_task(document_service.parse_document, doc.id)
    return UploadResponse(document_id=doc.id, name=doc.name, status="parsing", message="文件已上传，正在解析")


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await document_service.delete_document(db, doc_id)
    return result


@router.post("/{doc_id}/reparse", response_model=DocumentOut)
async def reparse_document(doc_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    doc = await document_service.get_document(db, doc_id)
    background_tasks.add_task(document_service.parse_document, doc.id)
    return doc


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
async def get_chunks(doc_id: int, db: AsyncSession = Depends(get_db)):
    return await document_service.get_chunks(db, doc_id)
