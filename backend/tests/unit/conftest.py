"""Shared fixtures for unit tests."""
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class FakeRow:
    id: uuid.UUID
    name: str
    color: str | None
    total: Decimal


class FakeResult:
    def __init__(self, rows: list[FakeRow]) -> None:
        self._rows = rows

    def all(self) -> list[FakeRow]:
        return self._rows


class FakeSession:
    """In-memory fake for AsyncSession. Returns pre-loaded rows on execute()."""

    def __init__(self, rows: list[FakeRow]) -> None:
        self._rows = rows

    async def execute(self, stmt: Any) -> FakeResult:
        return FakeResult(self._rows)
