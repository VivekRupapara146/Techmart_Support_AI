"""
Shared response models so every endpoint returns a consistent shape.
"""
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None


class ErrorDetail(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
