from pydantic import BaseModel


class EntityOut(BaseModel):
    id: str
    name: str
    entity_type: str
    description: str = ""
    properties: dict = {}


class EntityCreate(BaseModel):
    name: str
    entity_type: str
    description: str = ""


class EntityUpdate(BaseModel):
    name: str | None = None
    entity_type: str | None = None
    description: str | None = None


class RelationOut(BaseModel):
    source: str
    target: str
    relation_type: str
    properties: dict = {}


class RelationCreate(BaseModel):
    source: str
    target: str
    relation_type: str
    description: str = ""


class GraphSearchResult(BaseModel):
    entities: list[EntityOut] = []
    relations: list[RelationOut] = []


class GraphStatsOut(BaseModel):
    entity_count: int = 0
    relation_count: int = 0
    entity_type_count: int = 0
