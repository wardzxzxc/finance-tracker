import uuid
from datetime import date as _date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    color: str | None
    icon: str | None


class PaymentMethodResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str


class TransactionCreate(BaseModel):
    amount: Annotated[Decimal, Field(gt=0)]
    category: str
    payment_method: str
    type: Literal["income", "expense"] = "expense"
    description: str | None = None
    date: _date | None = None
    with_partner: bool = False


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    type: str
    category: CategoryResponse
    payment_method: PaymentMethodResponse | None
    description: str | None
    date: _date
    with_partner: bool
    created_at: datetime
