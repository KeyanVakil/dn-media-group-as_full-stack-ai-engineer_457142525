from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: UUID
    name: str
    type: str
    description: str | None
    article_count: int

    model_config = {"from_attributes": True}


class EntityArticleSource(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class EntityArticleItem(BaseModel):
    id: UUID
    title: str
    source: EntityArticleSource
    published_at: datetime | None
    analyzed: bool
    ingested_at: datetime

    model_config = {"from_attributes": True}


class EntityDetailResponse(BaseModel):
    id: UUID
    name: str
    type: str
    description: str | None
    article_count: int
    articles: list[EntityArticleItem] = []


class ConnectionNode(BaseModel):
    id: UUID
    name: str
    type: str
    article_count: int


class ConnectionEdge(BaseModel):
    source: UUID
    target: UUID
    strength: float
    evidence_count: int


class ConnectionsResponse(BaseModel):
    center: ConnectionNode
    nodes: list[ConnectionNode]
    edges: list[ConnectionEdge]
