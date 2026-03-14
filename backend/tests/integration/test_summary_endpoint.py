"""Integration tests for GET /api/transactions/summary."""
import os
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import TransactionType
from tests.integration.conftest import (
    make_category,
    make_payment_method,
    make_transaction,
)

API_KEY = os.environ.get("API_KEY", "changeme")
HEADERS = {"X-API-Key": API_KEY}


async def test_summary_by_category_returns_200(
    client: AsyncClient, db: AsyncSession
) -> None:
    food = await make_category(db, "Food-integ1", "#FF0000")
    transport = await make_category(db, "Transport-integ1", "#0000FF")
    await make_transaction(
        db, Decimal("500"), TransactionType.expense, food, date(2026, 3, 10)
    )
    await make_transaction(
        db, Decimal("200"), TransactionType.expense, transport, date(2026, 3, 15)
    )
    await db.commit()

    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    names = {g["name"] for g in body["groups"]}
    assert "Food-integ1" in names
    assert "Transport-integ1" in names
    assert float(body["total"]) == pytest.approx(700.0)


async def test_summary_by_payment_method_returns_200(
    client: AsyncClient, db: AsyncSession
) -> None:
    food = await make_category(db, "Food-integ2")
    visa = await make_payment_method(db, "Visa-integ2")
    amex = await make_payment_method(db, "Amex-integ2")
    await make_transaction(
        db,
        Decimal("300"),
        TransactionType.expense,
        food,
        date(2026, 3, 5),
        payment_method=visa,
    )
    await make_transaction(
        db,
        Decimal("100"),
        TransactionType.expense,
        food,
        date(2026, 3, 6),
        payment_method=amex,
    )
    await db.commit()

    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "payment_method"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    names = {g["name"] for g in body["groups"]}
    assert "Visa-integ2" in names
    assert "Amex-integ2" in names


async def test_summary_excludes_income(
    client: AsyncClient, db: AsyncSession
) -> None:
    cat = await make_category(db, "Salary-integ3")
    await make_transaction(
        db, Decimal("1000"), TransactionType.income, cat, date(2026, 3, 1)
    )
    await make_transaction(
        db, Decimal("50"), TransactionType.expense, cat, date(2026, 3, 1)
    )
    await db.commit()

    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    # Only the $50 expense should be in the total for this specific category
    matching = [g for g in body["groups"] if g["name"] == "Salary-integ3"]
    assert len(matching) == 1
    assert float(matching[0]["amount"]) == pytest.approx(50.0)


async def test_summary_empty_month_returns_empty_groups(
    client: AsyncClient, db: AsyncSession
) -> None:
    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 1, "year": 2000, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["groups"] == []
    assert float(body["total"]) == 0.0


async def test_summary_groups_sorted_high_to_low(
    client: AsyncClient, db: AsyncSession
) -> None:
    cheap = await make_category(db, "Cheap-integ5", "#111111")
    expensive = await make_category(db, "Expensive-integ5", "#222222")
    await make_transaction(
        db, Decimal("50"), TransactionType.expense, cheap, date(2026, 3, 20)
    )
    await make_transaction(
        db, Decimal("900"), TransactionType.expense, expensive, date(2026, 3, 20)
    )
    await db.commit()

    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    groups = resp.json()["groups"]
    # Filter to our test categories only
    our_groups = [
        g
        for g in groups
        if g["name"] in ("Cheap-integ5", "Expensive-integ5")
    ]
    assert float(our_groups[0]["amount"]) > float(our_groups[1]["amount"])


async def test_summary_missing_month_param_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.get(
        "/api/transactions/summary",
        params={"year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_summary_invalid_month_value_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 13, "year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_summary_invalid_group_by_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "foobar"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_summary_percentage_sums_approximately_100(
    client: AsyncClient, db: AsyncSession
) -> None:
    cat_a = await make_category(db, "A-integ9", "#AAAAAA")
    cat_b = await make_category(db, "B-integ9", "#BBBBBB")
    cat_c = await make_category(db, "C-integ9", "#CCCCCC")
    await make_transaction(
        db, Decimal("333"), TransactionType.expense, cat_a, date(2026, 4, 1)
    )
    await make_transaction(
        db, Decimal("333"), TransactionType.expense, cat_b, date(2026, 4, 1)
    )
    await make_transaction(
        db, Decimal("334"), TransactionType.expense, cat_c, date(2026, 4, 1)
    )
    await db.commit()

    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 4, "year": 2026, "group_by": "category"},
        headers=HEADERS,
    )
    assert resp.status_code == 200
    groups = resp.json()["groups"]
    our = [g for g in groups if g["name"] in ("A-integ9", "B-integ9", "C-integ9")]
    total_pct = sum(g["percentage"] for g in our)
    assert abs(total_pct - 100.0) <= 0.4  # rounding tolerance


async def test_summary_missing_auth_returns_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/transactions/summary",
        params={"month": 3, "year": 2026, "group_by": "category"},
    )
    assert resp.status_code == 401
