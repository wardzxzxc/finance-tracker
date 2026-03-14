import uuid
from typing import Literal

from pydantic import BaseModel, Field


class SummaryQueryParams(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=1000, le=9999)
    group_by: Literal["category", "payment_method"]


class SummaryGroup(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    amount: float
    percentage: float


class SummaryResponse(BaseModel):
    month: int
    year: int
    group_by: str
    total: float
    groups: list[SummaryGroup]
