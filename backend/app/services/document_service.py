import asyncio
import logging
import os
import shutil
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.chunk import Chunk
from app.exceptions import NotFoundError
from app.parsers.pipeline import process_document
from app.core.graph_build_service import extract_and_build
from app.services import graph_service
from app.db.chroma import get_or_create_collection
from app.db.mysql import async_session
from app.utils.pagination import PageParams, PageResult

logger = logging.getLogger("app")

UPLOAD_DIR = "uploads"

# 内存级处理锁：防止同一文档被并发解析导致死锁
_processing_locks: dict[int, asyncio.Lock] = {}


async def upload_document(db: AsyncSession, file_name: str, file_path: str, file_type: str, file_size: int, user_id: int) -> Document:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    doc = Document(name=file_name, file_path=file_path, file_type=file_type, file_size=file_size, status="pending", uploaded_by=user_id)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


def decide_document_status_after_graph(doc: Document, graph_result: dict):
    if graph_result.get("success"):
        doc.status = "completed"
        doc.error_message = None
        return

    doc.status = "graph_failed"
    message = graph_result.get("message") or "知识图谱构建失败"
    doc.error_message = f"文档解析完成，但知识图谱构建失败：{message}"[:500]


async def parse_document(doc_id: int):
    """后台任务: 用独立会话避免 FastAPI 依赖注入的 session 已关闭"""
    # 防止同一文档被并发解析（造成死锁）
    lock = _processing_locks.setdefault(doc_id, asyncio.Lock())
    if lock.locked():
        logger.warning(f"文档 {doc_id} 正在解析中，跳过重复请求")
        return
    async with lock:
        try:
            del _processing_locks[doc_id]
        except KeyError:
            pass

        async with async_session() as db:
            doc = await get_document(db, doc_id)
            doc.status = "parsing"
            await db.commit()
            try:
                content = await process_document(doc.file_path, doc.id)
                chunk_count = (await db.execute(
                    select(func.count()).select_from(Chunk).where(Chunk.document_id == doc_id)
                )).scalar() or 0
                doc.chunk_count = chunk_count

                # 构建知识图谱
                doc.status = "building_graph"
                await db.commit()
                try:
                    await graph_service.delete_by_document(doc.id)
                    graph_result = await extract_and_build(content.text, doc.id)
                    decide_document_status_after_graph(doc, graph_result)
                except Exception as graph_err:
                    doc.status = "graph_failed"
                    doc.error_message = f"文档解析完成，但知识图谱构建异常：{str(graph_err)[:400]}"
            except Exception as e:
                doc.status = "failed"
                doc.error_message = str(e)[:500]
            await db.commit()


async def get_document(db: AsyncSession, doc_id: int) -> Document:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise NotFoundError("文档不存在")
    return doc


async def list_documents(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    file_type: str | None = None,
    status: str | None = None,
) -> PageResult:
    query = select(Document)
    count_query = select(func.count()).select_from(Document)

    if keyword:
        query = query.where(Document.name.contains(keyword))
        count_query = count_query.where(Document.name.contains(keyword))
    if file_type:
        query = query.where(Document.file_type == file_type)
        count_query = count_query.where(Document.file_type == file_type)
    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    if page_size <= 0:
        result = await db.execute(query.order_by(Document.created_at.desc()))
        items = list(result.scalars().all())
        response_page_size = total or len(items) or 1
        return PageResult.create(items=items, total=total, page=1, page_size=response_page_size)

    params = PageParams(page=page, page_size=page_size)
    result = await db.execute(query.order_by(Document.created_at.desc()).offset(params.offset).limit(params.page_size))
    items = list(result.scalars().all())
    return PageResult.create(items=items, total=total, page=page, page_size=page_size)


async def get_document_stats(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count()).select_from(Document))).scalar() or 0
    completed = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "completed"))).scalar() or 0
    parsing = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "parsing"))).scalar() or 0
    building_graph = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "building_graph"))).scalar() or 0
    graph_failed = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "graph_failed"))).scalar() or 0
    pending = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "pending"))).scalar() or 0
    failed = (await db.execute(select(func.count()).select_from(Document).where(Document.status == "failed"))).scalar() or 0
    return {
        "total": total,
        "completed": completed,
        "parsing": parsing,
        "building_graph": building_graph,
        "graph_failed": graph_failed,
        "pending": pending,
        "failed": failed,
    }


async def delete_document(db: AsyncSession, doc_id: int):
    doc = await get_document(db, doc_id)
    warnings = []

    # 1. 删除 Neo4j 知识图谱节点（非关键操作）
    try:
        graph_result = await graph_service.delete_by_document(doc_id)
        if not graph_result.get("neo4j"):
            warnings.append(f"图谱节点删除: {graph_result.get('error', '无数据')}")
    except Exception as e:
        warnings.append(f"图谱节点删除异常: {e}")

    # 2. 删除 ChromaDB 向量数据（非关键操作）
    try:
        collection = get_or_create_collection()
        await asyncio.to_thread(collection.delete, where={"document_id": doc_id})
    except Exception as e:
        warnings.append(f"向量数据删除: {e}")

    # 3. 删除物理文件（非关键操作）
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        warnings.append(f"物理文件删除: {e}")

    # 4. 删除 MySQL 中的 Chunk 和 Document 记录（关键操作）
    try:
        chunks_result = await db.execute(select(Chunk).where(Chunk.document_id == doc_id))
        chunks = chunks_result.scalars().all()
        for chunk in chunks:
            await db.delete(chunk)
        await db.delete(doc)
        await db.commit()
    except Exception as e:
        await db.rollback()
        return {"success": False, "message": f"数据库删除失败: {e}"}

    # MySQL 删除成功，返回成功（警告信息仅用于日志）
    if warnings:
        return {"success": True, "message": "文档已删除", "warnings": warnings}
    return {"success": True, "message": "文档及相关数据已删除"}


async def cleanup_orphaned_data(db: AsyncSession) -> dict:
    """清理孤儿数据：MySQL 中已删除但 Neo4j/ChromaDB 中残留的图谱和向量数据。"""
    warnings = []

    # 获取现有文档 ID 列表
    result = await db.execute(select(Document.id))
    existing_ids = [row[0] for row in result.fetchall()]

    # 清理 Neo4j 孤儿实体
    try:
        graph_result = await graph_service.cleanup_orphaned_entities(existing_ids)
        if graph_result.get("success"):
            deleted = graph_result.get("deleted_orphaned", 0) + graph_result.get("deleted_disconnected", 0)
            if deleted > 0:
                logger.info(f"清理孤儿图谱实体: {deleted} 个")
        else:
            warnings.append(f"图谱清理: {graph_result.get('error')}")
    except Exception as e:
        warnings.append(f"图谱清理异常: {e}")

    # 清理 ChromaDB 孤儿向量
    try:
        collection = get_or_create_collection()
        all_data = collection.get(include=["metadatas"])
        orphaned_ids = []
        for i, meta in enumerate(all_data.get("metadatas", [])):
            doc_id = (meta or {}).get("document_id")
            if doc_id is not None and doc_id not in existing_ids:
                orphaned_ids.append(all_data["ids"][i])
        if orphaned_ids:
            # ChromaDB delete 限制批次大小
            for batch_start in range(0, len(orphaned_ids), 5000):
                batch = orphaned_ids[batch_start:batch_start + 5000]
                await asyncio.to_thread(collection.delete, ids=batch)
            logger.info(f"清理孤儿向量: {len(orphaned_ids)} 个")
    except Exception as e:
        warnings.append(f"向量清理异常: {e}")

    return {"success": True, "existing_docs": len(existing_ids), "warnings": warnings}


async def get_chunks(db: AsyncSession, doc_id: int) -> list[Chunk]:
    result = await db.execute(select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index))
    return list(result.scalars().all())


async def delete_all_documents(db: AsyncSession) -> dict:
    """清空所有文档和相关数据"""
    warnings = []

    # 1. 获取所有文档
    result = await db.execute(select(Document))
    docs = result.scalars().all()

    # 2. 逐个删除（确保每个文档的数据都被清理）
    for doc in docs:
        delete_result = await delete_document(db, doc.id)
        if not delete_result.get("success"):
            warnings.append(f"删除文档 {doc.name}: {delete_result.get('message')}")

    # 3. 清空 Neo4j 所有剩余节点（非关键操作）
    try:
        await graph_service.delete_all_entities()
    except Exception as e:
        warnings.append(f"清空Neo4j: {e}")

    return {"success": True, "message": f"已清空 {len(docs)} 个文档及相关数据", "warnings": warnings}


async def delete_user_documents(db: AsyncSession, user_id: int) -> dict:
    """删除用户的所有文档及相关数据"""
    result = await db.execute(select(Document).where(Document.uploaded_by == user_id))
    docs = result.scalars().all()
    warnings = []

    for doc in docs:
        delete_result = await delete_document(db, doc.id)
        if not delete_result.get("success"):
            warnings.append(f"删除文档 {doc.name}: {delete_result.get('message')}")

    return {"success": True, "message": f"已清空 {len(docs)} 个旧文档", "warnings": warnings}
