import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.payment_method import PaymentMethod
from app.models.transaction import Transaction, TransactionType
from app.schemas.transaction import (
    CategoryResponse,
    PaymentMethodResponse,
    TransactionCreate,
    TransactionResponse,
)


async def create_transaction(
    db: AsyncSession,
    data: TransactionCreate,
) -> TransactionResponse:
    # Resolve category — case-insensitive name lookup
    result = await db.execute(select(Category))
    all_categories = result.scalars().all()
    category = next(
        (c for c in all_categories if c.name.lower() == data.category.lower()),
        None,
    )
    if category is None:
        names = ", ".join(sorted(c.name for c in all_categories))
        raise ValueError(
            f"Category '{data.category}' not found. Valid categories: {names}"
        )

    # Resolve payment method — case-insensitive name lookup
    result = await db.execute(select(PaymentMethod))
    all_payment_methods = result.scalars().all()
    payment_method = next(
        (pm for pm in all_payment_methods if pm.name.lower() == data.payment_method.lower()),
        None,
    )
    if payment_method is None:
        names = ", ".join(sorted(pm.name for pm in all_payment_methods))
        raise ValueError(
            f"Payment method '{data.payment_method}' not found. Valid payment methods: {names}"
        )

    tx_date = data.date if data.date is not None else date.today()

    tx = Transaction(
        id=uuid.uuid4(),
        amount=data.amount,
        type=TransactionType(data.type),
        category_id=category.id,
        payment_method_id=payment_method.id,
        description=data.description,
        date=tx_date,
        with_partner=data.with_partner,
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)

    return TransactionResponse(
        id=tx.id,
        amount=tx.amount,
        type=tx.type.value,
        category=CategoryResponse(
            id=category.id,
            name=category.name,
            color=category.color,
            icon=category.icon,
        ),
        payment_method=PaymentMethodResponse(
            id=payment_method.id,
            name=payment_method.name,
            type=payment_method.type.value,
        ),
        description=tx.description,
        date=tx.date,
        with_partner=tx.with_partner,
        created_at=tx.created_at,
    )
