from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.payment_method import PaymentMethod
from app.models.transaction import Transaction, TransactionType
from app.schemas.summary import SummaryGroup, SummaryResponse

_COLOR_FALLBACK = "#888888"


async def get_expense_summary(
    db: AsyncSession,
    month: int,
    year: int,
    group_by: Literal["category", "payment_method"],
) -> SummaryResponse:
    if group_by == "category":
        stmt = (
            select(
                Category.id,
                Category.name,
                Category.color,
                func.sum(Transaction.amount).label("total"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.type == TransactionType.expense,
                func.extract("month", Transaction.date) == month,
                func.extract("year", Transaction.date) == year,
            )
            .group_by(Category.id, Category.name, Category.color)
            .order_by(func.sum(Transaction.amount).desc())
        )
    else:
        stmt = (
            select(
                PaymentMethod.id,
                PaymentMethod.name,
                PaymentMethod.color,
                func.sum(Transaction.amount).label("total"),
            )
            .join(Transaction, Transaction.payment_method_id == PaymentMethod.id)
            .where(
                Transaction.type == TransactionType.expense,
                func.extract("month", Transaction.date) == month,
                func.extract("year", Transaction.date) == year,
            )
            .group_by(PaymentMethod.id, PaymentMethod.name, PaymentMethod.color)
            .order_by(func.sum(Transaction.amount).desc())
        )

    result = await db.execute(stmt)
    rows = result.all()

    total: Decimal = sum((row.total for row in rows), Decimal("0"))

    groups: list[SummaryGroup] = []
    for row in rows:
        if total > 0:
            percentage = round(float(row.total / total * 100), 1)
        else:
            percentage = 0.0
        groups.append(
            SummaryGroup(
                id=row.id,
                name=row.name,
                color=row.color or _COLOR_FALLBACK,
                amount=row.total,
                percentage=percentage,
            )
        )

    groups.sort(key=lambda g: g.amount, reverse=True)

    return SummaryResponse(
        month=month,
        year=year,
        group_by=group_by,
        total=total,
        groups=groups,
    )
