from fastapi import APIRouter, Depends
from app.dependencies import require_admin
from app.services import graph_service
from app.schemas.graph import (
    GraphSearchResult, EntityOut, EntityCreate, EntityUpdate,
    RelationOut, RelationCreate, GraphStatsOut,
)

router = APIRouter(prefix="/api/graph", tags=["知识图谱"])


def _to_entity_out(e: dict) -> EntityOut:
    props = {k: v for k, v in e.items() if k not in ("id", "name", "type", "description")}
    return EntityOut(
        id=str(e.get("id", "")),
        name=e.get("name", ""),
        entity_type=e.get("type", ""),
        description=e.get("description", ""),
        properties=props,
    )


@router.get("/entities", response_model=list[EntityOut])
async def get_entities(q: str = "", limit: int = 20, entity_type: str | None = None):
    results = await graph_service.search_entities(q, limit, entity_type)
    return [_to_entity_out(e) for e in results]


@router.post("/entities", response_model=EntityOut)
async def create_entity(body: EntityCreate, _admin: dict = Depends(require_admin)):
    result = await graph_service.create_entity(body.name, body.entity_type, body.description)
    if not result:
        from app.exceptions import AppError
        raise AppError("创建实体失败", status_code=500)
    return _to_entity_out(result)


@router.put("/entities/{entity_id}", response_model=dict)
async def update_entity(entity_id: str, body: EntityUpdate, _admin: dict = Depends(require_admin)):
    ok = await graph_service.update_entity(entity_id, body.name, body.entity_type, body.description)
    return {"success": ok}


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str, _admin: dict = Depends(require_admin)):
    ok = await graph_service.delete_entity(entity_id)
    return {"success": ok}


@router.get("/relations", response_model=list[RelationOut])
async def get_relations(limit: int = 100):
    results = await graph_service.get_relations(limit)
    return [RelationOut(source=r.get("source", ""), target=r.get("target", ""), relation_type=r.get("relation_type", "")) for r in results]


@router.post("/relations", response_model=RelationOut)
async def create_relation(body: RelationCreate, _admin: dict = Depends(require_admin)):
    result = await graph_service.create_relation(body.source, body.target, body.relation_type, body.description)
    if not result:
        from app.exceptions import AppError
        raise AppError("创建关系失败 — 请确认起始和目标实体存在", status_code=400)
    return RelationOut(**result)


@router.delete("/relations")
async def delete_relation(source: str, target: str, relation_type: str, _admin: dict = Depends(require_admin)):
    ok = await graph_service.delete_relation(source, target, relation_type)
    return {"success": ok}


@router.get("/search", response_model=GraphSearchResult)
async def search_graph(q: str = "", entity_type: str | None = None):
    entities = await graph_service.search_entities(q, entity_type=entity_type)
    entity_outs = [_to_entity_out(e) for e in entities]
    return GraphSearchResult(entities=entity_outs, relations=[])


@router.get("/stats", response_model=GraphStatsOut)
async def get_stats():
    return await graph_service.get_graph_stats()


@router.post("/cleanup-low-quality")
async def cleanup_low_quality_entities(limit: int = 5000, _admin: dict = Depends(require_admin)):
    return await graph_service.cleanup_low_quality_entities(limit=limit)
