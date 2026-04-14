from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ArticleSummaryResponse(BaseModel):
    summary: str
    topics: list[str]
    key_facts: list[str]

    model_config = {"from_attributes": True}


class ArticleEntityResponse(BaseModel):
    id: UUID
    name: str
    type: str
    sentiment: float
    relevance: float

    model_config = {"from_attributes": True}


class ArticleSourceResponse(BaseModel):
    id: UUID
    name: str

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    id: UUID
    title: str
    source: ArticleSourceResponse
    published_at: datetime | None
    analyzed: bool
    ingested_at: datetime

    model_config = {"from_attributes": True}


class ArticleDetailResponse(BaseModel):
    id: UUID
    source: ArticleSourceResponse
    title: str
    content: str
    author: str | None
    published_at: datetime | None
    ingested_at: datetime
    analyzed: bool
    summary: ArticleSummaryResponse | None = None
    entities: list[ArticleEntityResponse] = []

    model_config = {"from_attributes": True}
