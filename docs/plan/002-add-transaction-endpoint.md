# Implementation Plan: Add Transaction Endpoint (iPhone Shortcuts-Friendly)

| Field | Value |
|-------|-------|
| **Plan #** | 002 |
| **Feature PRD** | [docs/features/002-add-transaction-endpoint.md](../features/002-add-transaction-endpoint.md) |
| **Status** | Ready to implement |
| **Created** | 2026-03-14 |

---

## Context

This plan covers the `POST /api/transactions` endpoint — the primary ingestion path for new transactions. It is designed for single-call use from an iPhone Shortcut: category and payment method are resolved by name, the date and type default to sensible values, and the response is human-readable.

### Codebase state at time of writing

Plan 001 (monthly expense breakdown chart) has been fully implemented:

- **Backend**: `app/schemas/summary.py`, `app/services/summary.py`, `app/api/transactions.py` (GET `/transactions/summary`), and `app/main.py` router registration all exist. `__init__.py` stubs are in place for `schemas/`, `services/`, and `api/`. Auth (`app/auth.py`) and DB (`app/db.py`) are in place.
- **Models**: `Transaction`, `Category`, `PaymentMethod`, `Budget` all exist in `app/models/`. The `Transaction` model already has the `with_partner` boolean column.
- **Tests**: `tests/unit/` and `tests/integration/` directories exist with `conftest.py` fixtures and tests for the summary endpoint. The integration `conftest.py` already provides DB setup/teardown fixtures.
- **Frontend**: Fully built out for the summary chart — providers, routing, design system, and chart components all exist. No frontend work is required for this feature.

Because the service infrastructure is already in place, this plan is **backend-only**. The work is: schemas → service → route → tests.

---

## Implementation Steps

### Step 1 — Backend: Pydantic schemas for the transaction endpoint

**File to create:** `backend/app/schemas/transaction.py`

Define the following Pydantic v2 models:

```
CategoryResponse          — nested in the transaction response
  id: UUID
  name: str
  color: str | None       — hex colour or null
  icon: str | None        — emoji or null

PaymentMethodResponse     — nested in the transaction response
  id: UUID
  name: str
  type: str               — "cash" | "credit" | "debit"

TransactionCreate         — request body
  amount: Decimal         — must be > 0 (Field gt=0)
  category: str           — category name, case-insensitive
  payment_method: str     — payment method name, case-insensitive
  type: Literal["income", "expense"]   — default "expense"
  description: str | None — default None
  date: date | None       — default None (service fills in today)
  with_partner: bool      — default False

TransactionResponse       — response body (201)
  id: UUID
  amount: Decimal         — 2 decimal places
  type: str
  category: CategoryResponse
  payment_method: PaymentMethodResponse | None
  description: str | None
  date: date
  with_partner: bool
  created_at: datetime
```

`TransactionResponse` must use `model_config = ConfigDict(from_attributes=True)` so it can be populated from ORM objects.

**PRD reference:** §5.1 request field table, §5.2 success response schema.

---

### Step 2 — Backend: Transaction service

**File to create:** `backend/app/services/transaction.py`

Create a single async function:

```python
async def create_transaction(
    db: AsyncSession,
    data: TransactionCreate,
) -> TransactionResponse
```

**Logic:**

1. **Resolve category** — query all `Category` rows; find the one whose `name.lower()` matches `data.category.lower()`. If not found, collect all names and raise `ValueError(f"Category '{data.category}' not found. Valid categories: {', '.join(sorted(names))}")`.

2. **Resolve payment method** — query all `PaymentMethod` rows; find the one whose `name.lower()` matches `data.payment_method.lower()`. If not found, raise `ValueError(f"Payment method '{data.payment_method}' not found. Valid payment methods: {', '.join(sorted(names))}")`.

3. **Resolve date** — use `data.date` if provided, otherwise use `date.today()` (server-side).

4. **Insert** — create a `Transaction` ORM instance with the resolved `category_id`, `payment_method_id`, `amount`, `type` (as `TransactionType` enum), `description`, `date`, and `with_partner`. Add to session and flush (not commit — let the route's session context manager commit). Refresh to populate server-generated fields (`id`, `created_at`).

5. **Return** — eagerly load the related `Category` and `PaymentMethod` rows (via `selectinload` or by re-querying after flush) and return a `TransactionResponse` built from the ORM objects.

**Category and payment method fetch strategy:** Use a single `SELECT * FROM categories` and `SELECT * FROM payment_methods` query respectively (not filtered). This fetches all names in one round-trip, which is used both for the match and for the "valid options" error message without a second query.

**PRD reference:** §5.3 error responses, §6.1 layer responsibilities, §6.2 name resolution.

---

### Step 3 — Backend: POST route in transactions.py

**File to modify:** `backend/app/api/transactions.py`

Add a `POST /transactions` route to the existing `APIRouter`:

```python
@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction_route(
    body: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    try:
        return await create_transaction(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
```

- `require_api_key` is already applied at the router level via `dependencies=[Depends(require_api_key)]` — no change needed.
- Route does no business logic — input is validated by Pydantic, errors from the service become `404` responses, happy path returns `201` with the full response schema.
- FastAPI will automatically return `422` for Pydantic validation failures (missing fields, invalid types, `amount <= 0`).

**PRD reference:** §5.1 endpoint spec, §5.3 error table, §6.1 layer responsibilities.

---

### Step 4 — Backend: Unit tests for the transaction service

**File to create:** `backend/tests/unit/test_transaction_service.py`

Use an in-memory fake for the database session (same pattern as `test_summary_service.py`). Inject controlled category and payment method data. Test the service function in isolation.

**Test cases:**

| # | Test name | Setup | Expected result |
|---|-----------|-------|-----------------|
| 1 | `test_create_transaction_happy_path_expense` | Valid category, payment method, amount=24.50, no date | Returns `TransactionResponse` with `type="expense"`, `date=today`, `with_partner=False` |
| 2 | `test_create_transaction_with_partner_true` | Same as above but `with_partner=True` | Response has `with_partner=True` |
| 3 | `test_create_transaction_income_type` | `type="income"` | Response has `type="income"` |
| 4 | `test_create_transaction_explicit_date` | `date="2026-01-15"` | Response has `date=date(2026, 1, 15)` |
| 5 | `test_create_transaction_category_lookup_is_case_insensitive` | Category stored as `"Food"`, request sends `"food"` | Resolves to the correct category; no error |
| 6 | `test_create_transaction_payment_method_lookup_is_case_insensitive` | Payment method stored as `"Visa"`, request sends `"VISA"` | Resolves correctly |
| 7 | `test_create_transaction_unknown_category_raises_value_error` | Category `"Food"` exists, request sends `"Groceries"` | `ValueError` raised; message contains `"Groceries"` and lists `"Food"` |
| 8 | `test_create_transaction_unknown_payment_method_raises_value_error` | Payment method `"Visa"` exists, request sends `"Amex"` | `ValueError` raised; message contains `"Amex"` and lists `"Visa"` |
| 9 | `test_create_transaction_defaults_type_to_expense` | No `type` in request | `type` in response is `"expense"` |
| 10 | `test_create_transaction_defaults_with_partner_to_false` | No `with_partner` in request | `with_partner` in response is `False` |

Each test uses its own fixture data; no shared mutable state between tests.

**PRD reference:** §8 acceptance criteria.

---

### Step 5 — Backend: Integration tests for the transaction endpoint

**File to create:** `backend/tests/integration/test_transaction_endpoint.py`

Use `pytest` + `httpx.AsyncClient` against the real test PostgreSQL database, re-using the DB fixtures from `tests/integration/conftest.py`. Each test inserts seed categories and payment methods as needed.

**Test cases:**

| # | Test name | Setup | Expected HTTP + body |
|---|-----------|-------|----------------------|
| 1 | `test_create_transaction_returns_201_with_full_response` | Category "Food", payment method "Visa" exist; send valid body with `with_partner: true` | 201, response matches `TransactionResponse` schema; `category.name == "Food"`, `payment_method.name == "Visa"`, `with_partner == true` |
| 2 | `test_create_transaction_with_partner_omitted_defaults_to_false` | Same seed; send body without `with_partner` | 201, `with_partner == false` |
| 3 | `test_create_transaction_income_type` | Same seed; send `type: "income"` | 201, `type == "income"` |
| 4 | `test_create_transaction_date_defaults_to_today` | Same seed; omit `date` | 201, `date` equals today's date |
| 5 | `test_create_transaction_unknown_category_returns_404` | No "Groceries" category; send `category: "Groceries"` | 404, detail contains `"Groceries"` and lists valid category names |
| 6 | `test_create_transaction_unknown_payment_method_returns_404` | No "Amex" payment method; send `payment_method: "Amex"` | 404, detail contains `"Amex"` and lists valid payment method names |
| 7 | `test_create_transaction_missing_amount_returns_422` | Omit `amount` | 422 |
| 8 | `test_create_transaction_missing_category_returns_422` | Omit `category` | 422 |
| 9 | `test_create_transaction_missing_payment_method_returns_422` | Omit `payment_method` | 422 |
| 10 | `test_create_transaction_zero_amount_returns_422` | `amount: 0` | 422 |
| 11 | `test_create_transaction_negative_amount_returns_422` | `amount: -5.00` | 422 |
| 12 | `test_create_transaction_invalid_type_returns_422` | `type: "transfer"` | 422 |
| 13 | `test_create_transaction_missing_api_key_returns_401` | No `X-API-Key` header | 401 |
| 14 | `test_create_transaction_invalid_api_key_returns_401` | Wrong `X-API-Key` value | 401 |

**PRD reference:** §8 acceptance criteria (integration test bullet).

---

## File Map

| # | File | Action |
|---|------|--------|
| 1 | `backend/app/schemas/transaction.py` | Create |
| 2 | `backend/app/services/transaction.py` | Create |
| 3 | `backend/app/api/transactions.py` | Modify (add POST route) |
| 4 | `backend/tests/unit/test_transaction_service.py` | Create |
| 5 | `backend/tests/integration/test_transaction_endpoint.py` | Create |

No frontend files. No new migrations (the `Transaction` model and all its columns already exist in the DB schema).

---

## Acceptance Criteria Mapping

Each item from PRD §8 maps to a specific implementation step and test.

| PRD Criterion | Covered by |
|---------------|------------|
| `POST /api/transactions` with valid body returns `201` | Step 3 route; Integration test #1 |
| `amount`, `category`, `payment_method` required; missing → `422` | Step 1 schema (no defaults); Integration tests #7, #8, #9 |
| `type` defaults to `"expense"` when omitted | Step 1 schema default; Unit test #9; Integration test #2 |
| `date` defaults to today when omitted | Step 2 service logic; Unit test #1; Integration test #4 |
| `with_partner` defaults to `false` when omitted | Step 1 schema default; Unit test #10; Integration test #2 |
| Category name lookup is case-insensitive | Step 2 service logic; Unit test #5 |
| Payment method name lookup is case-insensitive | Step 2 service logic; Unit test #6 |
| Unknown category → `404` with valid names listed | Step 2 service + Step 3 route; Unit test #7; Integration test #5 |
| Unknown payment method → `404` with valid names listed | Step 2 service + Step 3 route; Unit test #8; Integration test #6 |
| `amount` must be positive; zero or negative → `422` | Step 1 schema (`gt=0`); Integration tests #10, #11 |
| `type` must be `"income"` or `"expense"`; other → `422` | Step 1 schema (`Literal`); Integration test #12 |
| Returns `401` if `X-API-Key` missing or wrong | Router-level dependency (already exists); Integration tests #13, #14 |
| Response matches `TransactionResponse` schema exactly | Step 1 schema + Step 3 `response_model`; Integration test #1 |
| Integration tests cover all acceptance criteria | Step 5 |

---

## Implementation Order

Follow Red-Green-Refactor within each step.

```
1 → schemas/transaction.py              (unblocks service + route)
2 → services/transaction.py             (core logic)
3 → api/transactions.py (POST route)    (wires route to service)
4 → unit tests                          (service tested in isolation)
5 → integration tests                   (full stack verified)
```
