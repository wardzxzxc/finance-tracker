# Feature PRD: Add Transaction Endpoint (iPhone Shortcuts-Friendly)

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-03-14 |
| **Author** | Edward Wang |

---

## 1. Overview

This feature implements `POST /api/transactions` — the primary way transactions enter the system. The endpoint is designed to be called directly from an iPhone Shortcut with minimal friction: category and payment method are looked up by name (not UUID), the date defaults to today, and the response is human-readable enough to display in a Shortcut notification.

---

## 2. Background & Motivation

The original PRD specifies iPhone Shortcuts as the primary transaction ingestion mechanism. Shortcuts can send HTTP POST requests with a JSON body, but they have no way to perform a prior lookup to resolve a UUID for a category or payment method — the request has to be a single self-contained call. The endpoint therefore must accept names (e.g., `"Food"`, `"Visa"`) rather than UUIDs, and resolve them server-side.

---

## 3. User Story

> As a user, I want to log a transaction from my iPhone by running a Shortcut that sends a single HTTP request, so that recording a purchase takes less than ten seconds.

---

## 4. User-Facing Behaviour

This is a purely backend feature — there is no new UI. The user-facing surface is the iPhone Shortcut that calls the endpoint.

### 4.1 The Shortcut Flow

A typical Shortcut:

1. Asks the user for an amount (number input).
2. Asks the user for a category (text or menu input, e.g., "Food").
3. Asks the user for a payment method (text or menu input, e.g., "Visa").
4. Asks the user "Split with partner?" (yes/no).
5. Optionally asks for a description.
6. Sends a single `POST /api/transactions` request with the collected values.
7. Displays the response (amount and category) in a notification or "Show Result" action.

### 4.2 Name Resolution

The caller passes `category` and `payment_method` as plain strings (case-insensitive). The server resolves them to the corresponding database records. If no match is found, the server returns a clear error listing valid options so the user can correct their Shortcut.

### 4.3 Date Defaulting

If `date` is omitted from the request, the transaction is recorded with today's date (server-side, in the server's local timezone). The caller may also pass an explicit ISO 8601 date string (`YYYY-MM-DD`) to backdate or future-date a transaction.

### 4.4 Transaction Type Defaulting

If `type` is omitted, it defaults to `"expense"` — the overwhelmingly common case for Shortcut usage. The caller may pass `"income"` explicitly when needed.

### 4.5 Split with Partner

An optional boolean field `with_partner` (default `false`) indicates whether this transaction was split with a partner. The Shortcut may present this as a yes/no prompt, but omitting the field entirely is valid and treated as `false`. This flag is stored on every transaction and used for later spending analysis (e.g., filtering out shared costs to see personal-only spend).

---

## 5. API Requirements

### 5.1 Endpoint

```
POST /api/transactions
```

**Authentication:** `X-API-Key` header required. Returns `401` if missing or invalid.

**Content-Type:** `application/json`

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `amount` | number | Yes | — | Transaction amount. Must be positive. |
| `category` | string | Yes | — | Category name, case-insensitive. Must match an existing category. |
| `payment_method` | string | Yes | — | Payment method name, case-insensitive. Must match an existing payment method. |
| `type` | string | No | `"expense"` | `"income"` or `"expense"`. |
| `description` | string | No | `null` | Free-text note. |
| `date` | string | No | today | ISO 8601 date string (`YYYY-MM-DD`). Defaults to today's date on the server. |
| `with_partner` | boolean | No | `false` | Whether this transaction was split with a partner. Defaults to `false` so Shortcuts that omit it are treated as personal expenses. |

**Example request body:**

```json
{
  "amount": 24.50,
  "category": "food",
  "payment_method": "visa",
  "description": "Lunch at Chipotle",
  "date": "2026-03-14",
  "with_partner": true
}
```

Minimal valid request (amount + category + payment method only):

```json
{
  "amount": 9.99,
  "category": "subscriptions",
  "payment_method": "visa"
}
```

---

### 5.2 Success Response — `201 Created`

```json
{
  "id": "3f2e1a00-...",
  "amount": 24.50,
  "type": "expense",
  "category": {
    "id": "9c4b2d00-...",
    "name": "Food",
    "color": "#FF6384",
    "icon": "🍔"
  },
  "payment_method": {
    "id": "7a1c3e00-...",
    "name": "Visa",
    "type": "credit"
  },
  "description": "Lunch at Chipotle",
  "date": "2026-03-14",
  "with_partner": false,
  "created_at": "2026-03-14T12:34:56Z"
}
```

`payment_method` is `null` in the response if none was provided.

---

### 5.3 Error Responses

| Status | Condition | Response body |
|--------|-----------|---------------|
| `401` | Missing or invalid `X-API-Key` | `{"detail": "Unauthorized"}` |
| `422` | Missing `amount`, `category`, or `payment_method`; invalid types | Standard FastAPI 422 body |
| `404` | Category name not found | `{"detail": "Category 'foo' not found. Valid categories: Food, Transport, ..."}` |
| `404` | Payment method name not found | `{"detail": "Payment method 'foo' not found. Valid payment methods: Visa, Cash, ..."}` |

The `404` error messages enumerate valid names so a Shortcut "Show Result" action gives the user actionable feedback.

---

### 5.4 No Changes to Existing Endpoints

No existing endpoints are modified for this feature.

---

## 6. Implementation Notes

### 6.1 Layer Responsibilities

Following project conventions:

- **Route** (`app/api/transactions.py`): validates input via Pydantic schema, calls service, returns `201` with response schema.
- **Service** (`app/services/transactions.py`): resolves category/payment-method names (case-insensitive DB lookup), raises `ValueError` with a human-readable message if not found, inserts the transaction row, returns the ORM object.
- **Route** converts `ValueError` from the service to `HTTPException(status_code=404)`.

### 6.2 Name Resolution

Category and payment method lookups must be case-insensitive (use `ilike` or `lower()`). The lookup fetches all names in a single query to build the "valid options" list for error messages without a second round-trip.

### 6.3 Schemas

Three new Pydantic schemas are needed:

- `TransactionCreate` — request body (fields described in §5.1).
- `CategoryResponse` — nested in the response (`id`, `name`, `color`, `icon`).
- `PaymentMethodResponse` — nested in the response (`id`, `name`, `type`).
- `TransactionResponse` — full response body (fields described in §5.2).

---

## 7. Out of Scope

- **Bulk ingestion** — only one transaction per request. Batch import is a separate feature.
- **Fuzzy name matching** — category/payment-method names must match exactly (case-insensitive). No auto-correction or partial matching.
- **Creating categories or payment methods on the fly** — unknown names are always an error; the user must pre-configure them.
- **Frontend UI for adding transactions** — a form-based UI is a separate feature.
- **Idempotency keys** — no deduplication. Sending the same Shortcut twice creates two transactions.

---

## 8. Acceptance Criteria

**Backend:**
- [ ] `POST /api/transactions` with valid body returns `201` and the created transaction in the response.
- [ ] `amount`, `category`, and `payment_method` are required; missing any of them returns `422`.
- [ ] `type` defaults to `"expense"` when omitted.
- [ ] `date` defaults to today's server date when omitted.
- [ ] `with_partner` defaults to `false` when omitted.
- [ ] Category name lookup is case-insensitive (`"food"` matches category `"Food"`).
- [ ] Payment method name lookup is case-insensitive.
- [ ] Unknown category name returns `404` with a message listing valid category names.
- [ ] Unknown payment method name returns `404` with a message listing valid payment method names.
- [ ] `amount` must be positive; zero or negative values return `422`.
- [ ] `type` must be `"income"` or `"expense"`; other values return `422`.
- [ ] Returns `401` if `X-API-Key` is missing or wrong.
- [ ] Response body matches the `TransactionResponse` schema exactly (no raw ORM fields).
- [ ] Integration tests cover: happy path with `with_partner: true`, happy path with `with_partner` omitted (defaults to `false`), happy path income, unknown category, unknown payment method, missing required fields, invalid auth.
