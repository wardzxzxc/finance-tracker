"""Unit tests for the transaction service.

Uses an in-memory FakeTransactionSession that simulates two sequential execute()
calls (categories, then payment methods) and the add/flush/refresh insert flow.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from app.models.payment_method import PaymentMethodType
from app.schemas.transaction import TransactionCreate
from app.services.transaction import create_transaction


# ── Fake model-like objects ───────────────────────────────────────────────────


class FakeCategory:
    def __init__(
        self,
        name: str,
        color: str | None = "#FF6384",
        icon: str | None = None,
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.color = color
        self.icon = icon


class FakePaymentMethod:
    def __init__(
        self,
        name: str,
        pm_type: PaymentMethodType = PaymentMethodType.credit,
    ) -> None:
        self.id = uuid.uuid4()
        self.name = name
        self.type = pm_type


class FakeScalarsResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class FakeExecuteResult:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalars(self) -> FakeScalarsResult:
        return FakeScalarsResult(self._items)


class FakeTransactionSession:
    """In-memory fake for AsyncSession used by create_transaction().

    Returns categories on the first execute() call and payment methods on the
    second. Supports add(), flush(), and refresh() to simulate the insert flow.
    """

    def __init__(
        self,
        categories: list[FakeCategory],
        payment_methods: list[FakePaymentMethod],
    ) -> None:
        self._queue: list[list[Any]] = [categories, payment_methods]
        self._call_count = 0
        self._added: list[Any] = []

    async def execute(self, stmt: Any) -> FakeExecuteResult:
        items = self._queue[self._call_count] if self._call_count < len(self._queue) else []
        self._call_count += 1
        return FakeExecuteResult(items)

    def add(self, obj: Any) -> None:
        self._added.append(obj)

    async def flush(self) -> None:
        pass

    async def refresh(self, obj: Any) -> None:
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime(2026, 3, 14, 12, 0, 0, tzinfo=timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_category(name: str = "Food") -> FakeCategory:
    return FakeCategory(name=name)


def make_payment_method(name: str = "Visa") -> FakePaymentMethod:
    return FakePaymentMethod(name=name)


def make_body(**overrides: Any) -> TransactionCreate:
    defaults: dict[str, Any] = {
        "amount": Decimal("24.50"),
        "category": "Food",
        "payment_method": "Visa",
    }
    defaults.update(overrides)
    return TransactionCreate(**defaults)


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_create_transaction_happy_path_expense() -> None:
    """Valid request returns expense with today's date and with_partner=False."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    result = await create_transaction(db, make_body())

    assert result.type == "expense"
    assert result.date == date.today()
    assert result.with_partner is False
    assert result.amount == Decimal("24.50")


async def test_create_transaction_with_partner_true() -> None:
    """with_partner=True is preserved in the response."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    result = await create_transaction(db, make_body(with_partner=True))

    assert result.with_partner is True


async def test_create_transaction_income_type() -> None:
    """type='income' is preserved in the response."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    result = await create_transaction(db, make_body(type="income"))

    assert result.type == "income"


async def test_create_transaction_explicit_date() -> None:
    """An explicit date is used rather than defaulting to today."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    result = await create_transaction(db, make_body(date=date(2026, 1, 15)))

    assert result.date == date(2026, 1, 15)


async def test_create_transaction_category_lookup_is_case_insensitive() -> None:
    """Category stored as 'Food' resolves when request sends 'food'."""
    db = FakeTransactionSession([make_category(name="Food")], [make_payment_method()])

    result = await create_transaction(db, make_body(category="food"))

    assert result.category.name == "Food"


async def test_create_transaction_payment_method_lookup_is_case_insensitive() -> None:
    """Payment method stored as 'Visa' resolves when request sends 'VISA'."""
    db = FakeTransactionSession([make_category()], [make_payment_method(name="Visa")])

    result = await create_transaction(db, make_body(payment_method="VISA"))

    assert result.payment_method is not None
    assert result.payment_method.name == "Visa"


async def test_create_transaction_unknown_category_raises_value_error() -> None:
    """Unknown category raises ValueError containing the name and valid options."""
    db = FakeTransactionSession([make_category(name="Food")], [make_payment_method()])

    with pytest.raises(ValueError) as exc_info:
        await create_transaction(db, make_body(category="Groceries"))

    detail = str(exc_info.value)
    assert "Groceries" in detail
    assert "Food" in detail


async def test_create_transaction_unknown_payment_method_raises_value_error() -> None:
    """Unknown payment method raises ValueError containing the name and valid options."""
    db = FakeTransactionSession([make_category()], [make_payment_method(name="Visa")])

    with pytest.raises(ValueError) as exc_info:
        await create_transaction(db, make_body(payment_method="Amex"))

    detail = str(exc_info.value)
    assert "Amex" in detail
    assert "Visa" in detail


async def test_create_transaction_defaults_type_to_expense() -> None:
    """Omitting type defaults to 'expense'."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    body = TransactionCreate(
        amount=Decimal("10.00"),
        category="Food",
        payment_method="Visa",
    )
    result = await create_transaction(db, body)

    assert result.type == "expense"


async def test_create_transaction_defaults_with_partner_to_false() -> None:
    """Omitting with_partner defaults to False."""
    db = FakeTransactionSession([make_category()], [make_payment_method()])

    body = TransactionCreate(
        amount=Decimal("10.00"),
        category="Food",
        payment_method="Visa",
    )
    result = await create_transaction(db, body)

    assert result.with_partner is False
