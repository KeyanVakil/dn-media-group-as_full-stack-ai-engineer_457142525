from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2048)
    category: str = Field(..., min_length=1, max_length=100)


class SourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    url: str | None = Field(None, min_length=1, max_length=2048)
    category: str | None = Field(None, min_length=1, max_length=100)
    active: bool | None = None


class SourceResponse(BaseModel):
    id: UUID
    name: str
    url: str
    category: str
    active: bool
    last_fetched_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
