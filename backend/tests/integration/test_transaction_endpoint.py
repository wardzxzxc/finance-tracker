"""Integration tests for POST /api/transactions."""
import os
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.conftest import make_category, make_payment_method

API_KEY = os.environ.get("API_KEY", "changeme")
HEADERS = {"X-API-Key": API_KEY}


async def test_create_transaction_returns_201_with_full_response(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Happy path with with_partner=true returns 201 and full response schema."""
    await make_category(db, "Food-tx1")
    await make_payment_method(db, "Visa-tx1")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={
            "amount": 24.50,
            "category": "Food-tx1",
            "payment_method": "Visa-tx1",
            "description": "Lunch at Chipotle",
            "date": "2026-03-14",
            "with_partner": True,
        },
        headers=HEADERS,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["type"] == "expense"
    assert float(body["amount"]) == pytest.approx(24.50)
    assert body["category"]["name"] == "Food-tx1"
    assert body["payment_method"]["name"] == "Visa-tx1"
    assert body["description"] == "Lunch at Chipotle"
    assert body["date"] == "2026-03-14"
    assert body["with_partner"] is True
    assert "id" in body
    assert "created_at" in body


async def test_create_transaction_with_partner_omitted_defaults_to_false(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Omitting with_partner returns with_partner=false in the response."""
    await make_category(db, "Food-tx2")
    await make_payment_method(db, "Visa-tx2")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={"amount": 9.99, "category": "Food-tx2", "payment_method": "Visa-tx2"},
        headers=HEADERS,
    )

    assert resp.status_code == 201
    assert resp.json()["with_partner"] is False


async def test_create_transaction_income_type(
    client: AsyncClient, db: AsyncSession
) -> None:
    """type='income' is stored and returned correctly."""
    await make_category(db, "Salary-tx3")
    await make_payment_method(db, "Cash-tx3")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={
            "amount": 5000.00,
            "category": "Salary-tx3",
            "payment_method": "Cash-tx3",
            "type": "income",
        },
        headers=HEADERS,
    )

    assert resp.status_code == 201
    assert resp.json()["type"] == "income"


async def test_create_transaction_date_defaults_to_today(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Omitting date uses today's server date."""
    await make_category(db, "Food-tx4")
    await make_payment_method(db, "Visa-tx4")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "category": "Food-tx4", "payment_method": "Visa-tx4"},
        headers=HEADERS,
    )

    assert resp.status_code == 201
    assert resp.json()["date"] == date.today().isoformat()


async def test_create_transaction_unknown_category_returns_404(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Unknown category returns 404 with detail listing valid category names."""
    await make_category(db, "Food-tx5")
    await make_payment_method(db, "Visa-tx5")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={
            "amount": 10.00,
            "category": "Groceries-unknown",
            "payment_method": "Visa-tx5",
        },
        headers=HEADERS,
    )

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "Groceries-unknown" in detail
    assert "Food-tx5" in detail


async def test_create_transaction_unknown_payment_method_returns_404(
    client: AsyncClient, db: AsyncSession
) -> None:
    """Unknown payment method returns 404 with detail listing valid names."""
    await make_category(db, "Food-tx6")
    await make_payment_method(db, "Visa-tx6")
    await db.commit()

    resp = await client.post(
        "/api/transactions",
        json={
            "amount": 10.00,
            "category": "Food-tx6",
            "payment_method": "Amex-unknown",
        },
        headers=HEADERS,
    )

    assert resp.status_code == 404
    detail = resp.json()["detail"]
    assert "Amex-unknown" in detail
    assert "Visa-tx6" in detail


async def test_create_transaction_missing_amount_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"category": "Food", "payment_method": "Visa"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_missing_category_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "payment_method": "Visa"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_missing_payment_method_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "category": "Food"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_zero_amount_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 0, "category": "Food", "payment_method": "Visa"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_negative_amount_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": -5.00, "category": "Food", "payment_method": "Visa"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_invalid_type_returns_422(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "category": "Food", "payment_method": "Visa", "type": "transfer"},
        headers=HEADERS,
    )
    assert resp.status_code == 422


async def test_create_transaction_missing_api_key_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "category": "Food", "payment_method": "Visa"},
    )
    assert resp.status_code == 401


async def test_create_transaction_invalid_api_key_returns_401(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={"amount": 10.00, "category": "Food", "payment_method": "Visa"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401
