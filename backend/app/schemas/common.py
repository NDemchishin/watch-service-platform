"""
Общие схемы для пагинации.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Базовая схема для пагинированных ответов."""
    items: list[T]
    total: int
    skip: int
    limit: int
