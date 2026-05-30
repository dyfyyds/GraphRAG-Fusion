import asyncio
from app.db.chroma import get_or_create_collection


async def upsert_vectors(ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]):
    collection = get_or_create_collection()
    await asyncio.to_thread(
        collection.upsert,
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


async def query_vectors(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    collection = get_or_create_collection()
    result = await asyncio.to_thread(
        collection.query,
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    items = []
    if result and result["ids"]:
        for i in range(len(result["ids"][0])):
            items.append({
                "id": result["ids"][0][i],
                "document": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            })
    return items


async def delete_by_document(document_id: int):
    collection = get_or_create_collection()
    await asyncio.to_thread(collection.delete, where={"document_id": document_id})
