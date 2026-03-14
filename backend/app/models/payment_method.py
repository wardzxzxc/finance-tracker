import enum
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PaymentMethodType(enum.Enum):
    cash = "cash"
    credit = "credit"
    debit = "debit"


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(7))
    type: Mapped[PaymentMethodType] = mapped_column(
        sa.Enum(PaymentMethodType, name="payment_method_type"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
