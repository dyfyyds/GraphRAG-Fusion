import asyncio
import logging

from app.parsers.base import ParsedContent
from app.parsers.pdf_parser import PDFParser
from app.parsers.docx_parser import DocxParser
from app.parsers.txt_parser import TxtParser
from app.parsers.md_parser import MdParser
from app.parsers.chunker import chunk_text
from app.core.embedding_client import get_embedding_client
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
    needle = chunk[:30].strip()
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
    chunks = chunk_text(content.text)

    # 3. Embedding（批量）
    embedding_client = get_embedding_client()
    embeddings = await embedding_client.embed_batch(chunks)

    # 4. 写入 ChromaDB（同步客户端，用线程池包裹）
    collection = get_or_create_collection()
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
    async with async_session() as db:
        for i, chunk_text_val in enumerate(chunks):
            page_number = _map_page(chunk_text_val, content.page_map)
            chunk = Chunk(
                document_id=document_id,
                content=chunk_text_val,
                chunk_index=i,
                page_number=page_number,
                vector_id=ids[i],
            )
            db.add(chunk)
        await db.commit()

    logger.info(f"文档 {document_id} 处理完成: {len(chunks)} 个分块已写入 ChromaDB + MySQL")
    return content
