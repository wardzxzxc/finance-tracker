"""Unit tests for the summary service.

The FakeSession returns pre-configured rows representing the result of the DB
query. This lets us test the processing logic (totals, percentages, sorting)
without a real database.
"""

import uuid
from decimal import Decimal

from app.services.summary import get_expense_summary
from tests.unit.conftest import FakeRow, FakeSession


def row(name: str, total: str, color: str = "#FF0000") -> FakeRow:
    return FakeRow(id=uuid.uuid4(), name=name, color=color, total=Decimal(total))


async def test_summary_returns_groups_sorted_by_amount_descending() -> None:
    """Groups are returned highest to lowest amount."""
    db = FakeSession([row("Food", "300"), row("Transport", "700")])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    assert result.groups[0].amount > result.groups[1].amount


async def test_summary_returns_empty_groups_when_no_expenses() -> None:
    """No expenses for the month → empty groups list and zero total."""
    db = FakeSession([])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    assert result.groups == []
    assert result.total == 0.0


async def test_summary_calculates_percentage_correctly() -> None:
    """Percentages reflect each group's share of the total."""
    db = FakeSession([row("A", "700"), row("B", "300")])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    assert result.groups[0].percentage == 70.0
    assert result.groups[1].percentage == 30.0


async def test_summary_groups_by_payment_method() -> None:
    """group_by=payment_method returns groups with correct names, amounts, and total."""
    db = FakeSession([row("Visa", "600", "#4169E1"), row("Amex", "200", "#00A651")])
    result = await get_expense_summary(
        db, month=3, year=2026, group_by="payment_method"
    )
    assert result.group_by == "payment_method"
    assert result.total == 800.0
    assert result.groups[0].name == "Visa"
    assert result.groups[0].amount == 600.0
    assert result.groups[1].name == "Amex"
    assert result.groups[1].amount == 200.0


async def test_summary_response_echoes_month_and_year() -> None:
    """month and year passed in are reflected in the response."""
    db = FakeSession([row("Food", "400")])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    assert result.month == 3
    assert result.year == 2026


async def test_summary_percentage_rounds_to_one_decimal() -> None:
    """Percentages are rounded to one decimal place."""
    db = FakeSession([row("A", "100"), row("B", "200"), row("C", "300")])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    total = 600.0
    for group in result.groups:
        raw = group.amount / total * 100
        assert group.percentage == round(raw, 1)


async def test_summary_uses_color_fallback_when_color_is_none() -> None:
    """Groups with null color receive the default fallback hex string."""
    fake_row = FakeRow(
        id=uuid.uuid4(), name="Uncategorised", color=None, total=Decimal("100")
    )
    db = FakeSession([fake_row])
    result = await get_expense_summary(db, month=3, year=2026, group_by="category")
    assert result.groups[0].color == "#888888"
