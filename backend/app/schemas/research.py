from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchCreate(BaseModel):
    query: str = Field(..., min_length=1)


class ResearchStepResponse(BaseModel):
    step_number: int
    action: str
    input_data: dict | None = None
    output_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchTaskResponse(BaseModel):
    id: UUID
    query: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResearchDetailResponse(BaseModel):
    id: UUID
    query: str
    status: str
    steps: list[ResearchStepResponse] = []
    result: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
