"""Integration test fixtures — real Postgres, no mocks."""
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import httpx
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_db
from app.main import app
from app.models.base import Base
from app.models.category import Category
from app.models.payment_method import PaymentMethod, PaymentMethodType
from app.models.transaction import Transaction, TransactionType

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", ""),
)

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def make_category(
    db: AsyncSession, name: str, color: str = "#FF6384"
) -> Category:
    cat = Category(id=uuid.uuid4(), name=name, color=color)
    db.add(cat)
    await db.flush()
    return cat


async def make_payment_method(
    db: AsyncSession,
    name: str,
    method_type: PaymentMethodType = PaymentMethodType.credit,
    color: str = "#36A2EB",
) -> PaymentMethod:
    pm = PaymentMethod(
        id=uuid.uuid4(), name=name, type=method_type, color=color
    )
    db.add(pm)
    await db.flush()
    return pm


async def make_transaction(
    db: AsyncSession,
    amount: Decimal,
    tx_type: TransactionType,
    category: Category,
    tx_date: date,
    payment_method: PaymentMethod | None = None,
) -> Transaction:
    tx = Transaction(
        id=uuid.uuid4(),
        amount=amount,
        type=tx_type,
        category_id=category.id,
        payment_method_id=payment_method.id if payment_method else None,
        date=tx_date,
    )
    db.add(tx)
    await db.flush()
    return tx
