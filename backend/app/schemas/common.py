from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[Any]
    meta: PaginationMeta


class SingleResponse(BaseModel, Generic[T]):
    data: Any
