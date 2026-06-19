import asyncio
import json
import os
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.mysql import get_db
from app.db.mysql import async_session
from app.dependencies import get_current_user
from app.schemas.documents import DocumentOut, DocumentListResponse, DocumentStatsOut, ChunkOut, UploadResponse
from app.services import document_service
from app.utils.file_utils import validate_file

router = APIRouter(prefix="/api/documents", tags=["知识库"])


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=1000),
    all: bool = Query(False),
    keyword: str | None = None,
    file_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    page_size = 0 if all else size
    result = await document_service.list_documents(db, page=page, page_size=page_size, keyword=keyword, file_type=file_type, status=status)
    return result


@router.get("/stats", response_model=DocumentStatsOut)
async def get_document_stats(db: AsyncSession = Depends(get_db)):
    return await document_service.get_document_stats(db)


@router.get("/events")
async def stream_document_events(_user: dict = Depends(get_current_user)):
    async def event_generator():
        last_signature = None
        while True:
            try:
                async with async_session() as db:
                    result = await document_service.list_documents(db, page=1, page_size=0)
                    payload = {
                        "items": [
                            DocumentOut.model_validate(item).model_dump(mode="json")
                            for item in result.items
                        ],
                        "total": result.total,
                        "page": result.page,
                        "page_size": result.page_size,
                        "pages": result.pages,
                    }

                signature = json.dumps(
                    [
                        [
                            item["id"],
                            item["status"],
                            item["chunk_count"],
                            item.get("error_message"),
                            item["updated_at"],
                        ]
                        for item in payload["items"]
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                )

                if signature != last_signature:
                    last_signature = signature
                    yield f"event: documents\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    yield ": heartbeat\n\n"
            except asyncio.CancelledError:
                break
            except Exception as exc:
                data = json.dumps({"message": str(exc)[:300]}, ensure_ascii=False)
                yield f"event: error\ndata: {data}\n\n"

            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/all")
async def delete_all_documents(db: AsyncSession = Depends(get_db)):
    """清空所有文档和相关数据"""
    result = await document_service.delete_all_documents(db)
    return result


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parse: bool = Query(True, description="是否在上传后自动开始解析"),
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
    if parse:
        background_tasks.add_task(document_service.parse_document, doc.id)
        return UploadResponse(document_id=doc.id, name=doc.name, status="parsing", message="文件已上传，正在解析")
    else:
        return UploadResponse(document_id=doc.id, name=doc.name, status="pending", message="文件已上传，待解析")


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    result = await document_service.delete_document(db, doc_id)
    return result


@router.post("/cleanup-orphans")
async def cleanup_orphaned_data(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """清理孤儿数据（Neo4j/ChromaDB 中残留的已删除文档数据）"""
    result = await document_service.cleanup_orphaned_data(db)
    return result


@router.post("/{doc_id}/reparse", response_model=DocumentOut)
async def reparse_document(doc_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    doc = await document_service.get_document(db, doc_id)
    background_tasks.add_task(document_service.parse_document, doc.id)
    return doc


@router.get("/{doc_id}/chunks", response_model=list[ChunkOut])
async def get_chunks(doc_id: int, db: AsyncSession = Depends(get_db)):
    return await document_service.get_chunks(db, doc_id)
