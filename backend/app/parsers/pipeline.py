import asyncio
import logging
import time

from sqlalchemy import delete, insert

from app.parsers.base import ParsedContent
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.parsers.txt_parser import TxtParser
from app.parsers.md_parser import MdParser
from app.parsers.chunker import chunk_text, is_structural_chunk, strip_breadcrumb
from app.core.embedding_client import get_embedding_client
from app.core.runtime_config import get_chunk_runtime_config
from app.db.chroma import get_or_create_collection
from app.db.mysql import async_session
from app.models.chunk import Chunk
from app.models.document import Document  # noqa: F401 — 注册到 SQLAlchemy metadata

logger = logging.getLogger("app")

PARSER_MAP = {
    ".pdf": PDFParser,
    ".docx": DocxParser,
    ".txt": TxtParser,
    ".md": MdParser,
}


def _map_page(chunk: str, page_map: list[dict]) -> int | None:
    """根据 chunk 内容的前30字符在 page_map 中定位源页码"""
    if not page_map:
        return None
    # 面包屑前缀是切分时附加的，不存在于原文，需剥离后再匹配页码
    needle = strip_breadcrumb(chunk)[:30].strip()
    for p in page_map:
        if needle in p.get("text", ""):
            return p.get("page")
    return None


async def process_document(file_path: str, document_id: int) -> ParsedContent:
    """完整流水线：解析 → 分块 → Embedding → ChromaDB → MySQL"""
    import os

    ext = os.path.splitext(file_path)[1].lower()
    parser_cls = PARSER_MAP.get(ext)
    if not parser_cls:
        raise ValueError(f"不支持的文件类型: {ext}")

    # 1. 解析（同步，用线程池避免阻塞）
    content = await asyncio.to_thread(parser_cls().parse, file_path)

    # 2. 分块
    chunk_config = await get_chunk_runtime_config()
    chunks = chunk_text(
        content.text,
        max_tokens=chunk_config.chunk_size,
        overlap=chunk_config.chunk_overlap,
    )
    if chunk_config.min_chunk_size:
        chunks = [
            chunk for chunk in chunks
            if len(chunk.strip()) >= chunk_config.min_chunk_size or is_structural_chunk(chunk)
        ]
    if not chunks and content.text.strip():
        chunks = [content.text.strip()[:chunk_config.chunk_size]]

    # 3. Embedding（批量）
    embedding_client = get_embedding_client()
    embeddings = await embedding_client.embed_batch(chunks)

    # 4. 写入 ChromaDB（同步客户端，用线程池包裹）
    collection = get_or_create_collection()
    try:
        await asyncio.to_thread(collection.delete, where={"document_id": document_id})
    except Exception as exc:
        logger.warning(f"删除文档 {document_id} 旧向量失败，继续覆盖写入: {exc}")

    ids = [f"doc_{document_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"document_id": document_id, "chunk_index": i} for i in range(len(chunks))]

    await asyncio.to_thread(
        collection.upsert,
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    # 5. 写入 MySQL（关键词检索 + 分块预览依赖此表）
    #    关键：DELETE 和 INSERT 分开提交，避免 gap lock 死锁
    chunk_rows = []
    for i, chunk_text_val in enumerate(chunks):
        page_number = _map_page(chunk_text_val, content.page_map)
        chunk_rows.append({
            "document_id": document_id,
            "content": chunk_text_val,
            "chunk_index": i,
            "page_number": page_number,
            "vector_id": ids[i],
        })

    # Phase 1: 先删除旧分块（独立事务，快速释放 gap lock）
    try:
        async with async_session() as db:
            await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
            await db.commit()
    except Exception as exc:
        logger.warning(f"文档 {document_id} 删除旧分块失败（可忽略重解析场景）: {str(exc)[:200]}")

    # Phase 2: 批量插入新分块（带死锁重试，最多 3 次）
    BATCH_SIZE = 200  # 每批最多 200 条，减少锁持有时间
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with async_session() as db:
                for batch_start in range(0, len(chunk_rows), BATCH_SIZE):
                    batch = chunk_rows[batch_start:batch_start + BATCH_SIZE]
                    if batch:
                        await db.execute(insert(Chunk).values(batch))
                await db.commit()
            break  # 成功，退出重试循环
        except Exception as exc:
            err_msg = str(exc)
            is_retryable = "1213" in err_msg or "1205" in err_msg or "Deadlock" in err_msg
            if is_retryable and attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    f"文档 {document_id} 分块写入死锁，第 {attempt+1}/{max_retries} 次重试，等待 {wait}s"
                )
                await asyncio.sleep(wait)
            else:
                logger.error(f"文档 {document_id} 分块写入失败: {err_msg[:500]}")
                raise

    logger.info(f"文档 {document_id} 处理完成: {len(chunks)} 个分块已写入 ChromaDB + MySQL")
    return content
