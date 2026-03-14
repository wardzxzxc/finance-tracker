# Feature PRD: Monthly Expense Breakdown Chart

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-03-14 |
| **Author** | Edward Wang |

---

## 1. Overview

This feature adds a pie chart to the dashboard that shows the user's expenses for a chosen month, broken down into slices. The user can choose *how* to break down the expenses (by category or by payment method) and *which month* to view. Both controls are visible on screen at all times, and the chart updates instantly whenever either one changes.

---

## 2. Background & Motivation

Currently there is no visual summary of spending. The user wants to be able to open the dashboard and immediately see where their money went in a given month — whether that's by spending category (Food, Transport, etc.) or by how they paid (credit card, cash, etc.). A pie chart is the right shape for this because it communicates proportions at a glance.

---

## 3. User Story

> As a user, I want to see my monthly expenses broken down by category or payment method on a pie chart, so I can quickly understand where my money is going.

---

## 4. User-Facing Behaviour

This section describes exactly what the user sees and can do. Implementation details come later.

### 4.1 The Chart

The dashboard contains a pie (or donut) chart. Each slice represents one group (either a category like "Food", or a payment method like "Visa"). The size of each slice is proportional to how much was spent in that group relative to the total for the month.

- **Slice labels:** each slice shows the group name and the dollar amount (e.g., "Food · $850").
- **Tooltip:** hovering or tapping a slice shows a small popup with the group name, total amount spent, and the percentage of total spend (e.g., "Food — $850.00 — 34.7%").
- **Only expenses are shown.** Income transactions are completely excluded. This chart is about where money went, not where it came from.
- **Zero-spend groups are hidden.** If the user has a "Gym" category but spent nothing on it this month, no slice appears for it.

### 4.2 Month Navigation

Above the chart, there is a month selector that shows the currently selected month and year (e.g., "March 2026"). The user can navigate between months using **left (←) and right (→) arrow buttons** on either side of the month label.

- Pressing **←** moves one month back (e.g., March → February).
- Pressing **→** moves one month forward (e.g., March → April).
- The **→ button is disabled when the user is already viewing the current month** — they cannot navigate into the future.
- There is no hard limit on how far back the user can navigate.
- When the month changes, the chart immediately updates to show data for the newly selected month.
- The default month shown when first opening the page is the **current calendar month**.

```
  ← | March 2026 | →
```
*(Arrow on the right is greyed out when viewing the current month)*

### 4.3 Group By Toggle

Below the month selector (or beside it on larger screens), there is a toggle or segmented control with two options:

- **Category** (default)
- **Payment Method**

Switching the toggle changes what each slice represents:

- **Category** mode: slices are Food, Transport, Entertainment, etc.
- **Payment Method** mode: slices are Visa, Amex, Cash, etc.

The chart re-renders immediately when the toggle changes. No page reload occurs.

### 4.4 Empty State

If the user selects a month with no recorded expense transactions, the chart area is replaced with a message:

> "No expenses recorded for [Month Year]. Add a transaction to see your breakdown."

No empty or broken chart is shown.

### 4.5 Filter State in the URL

The selected month and group-by value are reflected in the page URL as query parameters, for example:

```
/dashboard?month=2026-03&groupBy=category
```

This means:
- The view is **bookmarkable** — the user can save or share a link to a specific month's view.
- **Refreshing the page** restores the same filters the user had selected, rather than resetting to the current month.
- If no query params are present, the defaults apply (current month, grouped by category).

---

## 5. API Requirements

### 5.1 New Endpoint

```
GET /api/transactions/summary
```

This endpoint accepts a month, year, and grouping dimension, and returns the aggregated expense totals for that period. The frontend calls this endpoint every time the user changes a filter.

**Authentication:** `X-API-Key` header required (same as all other endpoints). Returns `401` if missing or invalid.

**Query Parameters:**

| Parameter | Type | Required | Valid Values | Description |
|-----------|------|----------|--------------|-------------|
| `month` | integer | Yes | 1–12 | The calendar month number (1 = January, 12 = December) |
| `year` | integer | Yes | Any 4-digit year | The calendar year |
| `group_by` | string | Yes | `"category"` or `"payment_method"` | How to group the expense totals |

**Validation errors return `422`** if a parameter is missing or out of range (e.g., `month=13`).

**Success Response — `200 OK`:**

```json
{
  "month": 3,
  "year": 2026,
  "group_by": "category",
  "total": 2450.00,
  "groups": [
    {
      "id": "3f2e1a...",
      "name": "Food",
      "color": "#FF6384",
      "amount": 850.00,
      "percentage": 34.7
    },
    {
      "id": "9c4b2d...",
      "name": "Transport",
      "color": "#36A2EB",
      "amount": 320.00,
      "percentage": 13.1
    }
  ]
}
```

**Response field notes:**

| Field | Description |
|-------|-------------|
| `total` | Sum of all expense amounts for the month, in dollars. |
| `groups` | Array of groups, sorted from highest to lowest `amount`. Empty array if there are no expenses. |
| `groups[].id` | The UUID of the category or payment method record. |
| `groups[].name` | Human-readable name (e.g., "Food", "Visa"). |
| `groups[].color` | Hex colour string used to colour the pie slice. For categories, this comes from the `categories.color` column. For payment methods, this comes from the `payment_methods.color` column. |
| `groups[].amount` | Total expenses in this group for the month, in dollars (2 decimal places). |
| `groups[].percentage` | This group's share of `total`, rounded to 1 decimal place (e.g., `34.7` means 34.7%). |

**Groups with zero spend are excluded from the response** — the array only contains groups where the user actually spent money.

### 5.2 No Changes to Existing Endpoints

No existing endpoints are modified for this feature.

---

## 6. Frontend Implementation

### 6.1 Where it Lives

This chart lives on the main dashboard page (`/dashboard`). It is one section of the dashboard — other sections (e.g., transaction list) remain unchanged.

### 6.2 Component Structure

```
pages/DashboardPage.tsx
  └── components/charts/ExpenseBreakdownChart.tsx   ← new component
        ├── MonthNavigator                           ← ← March 2026 →
        ├── GroupByToggle                            ← Category | Payment Method
        └── PieChartDisplay                         ← Recharts PieChart wrapper
```

- `ExpenseBreakdownChart` owns the filter state (selected month, selected groupBy) and the data-fetching query.
- `MonthNavigator`, `GroupByToggle`, and `PieChartDisplay` are presentational — they receive props and emit events.

### 6.3 Data Fetching

- Use TanStack Query (`useQuery`) with a cache key of `['expense-summary', year, month, groupBy]`.
- Any change to `year`, `month`, or `groupBy` automatically triggers a new fetch.
- While data is loading, show a loading skeleton (a grey placeholder in the shape of the chart area) — do not show a spinner over the old chart.
- If the fetch fails, show an error toast: "Failed to load expense summary. Please try again."

### 6.4 URL Sync

- On mount, read `month` and `groupBy` from the URL query params and use them as the initial filter state.
- Whenever the user changes a filter, update the URL query params without a full page navigation (use `history.replaceState` or the React Router equivalent).
- If URL params are missing or invalid, fall back to defaults (current month, `groupBy=category`).

### 6.5 Responsive Layout

The chart must work on a 390px wide screen (iPhone) as well as desktop.

| Screen size | Layout |
|-------------|--------|
| Mobile (< 768px) | Month navigator and group-by toggle stack vertically above the chart. Legend appears below the chart. |
| Desktop (≥ 768px) | Month navigator and group-by toggle sit side by side above the chart. Legend appears to the right of the chart. |

Touch targets for the arrow buttons must be at least 44×44px.

---

## 7. Out of Scope

The following are explicitly **not** part of this feature. They may be addressed in future features.

- **Drilling into transactions from a slice** — clicking a slice does not navigate to a filtered transaction list.
- **Income breakdown** — this chart shows expenses only. A separate income breakdown chart is a separate feature.
- **Custom date ranges** — only full calendar months are supported (no "last 30 days" or custom ranges).
- **Exporting the chart** — no image download or share functionality.
- **Editing categories or payment methods** from this view.

---

## 8. Acceptance Criteria

A developer can use this checklist to verify the feature is complete before it is marked done.

**Backend:**
- [ ] `GET /api/transactions/summary?month=3&year=2026&group_by=category` returns correct aggregated expense totals grouped by category.
- [ ] `GET /api/transactions/summary?month=3&year=2026&group_by=payment_method` returns correct aggregated expense totals grouped by payment method.
- [ ] Income transactions (`type = 'income'`) are excluded from all totals.
- [ ] Groups with zero spend do not appear in the response.
- [ ] `groups` array is sorted from highest to lowest `amount`.
- [ ] `percentage` values in the response sum to 100% (allowing for rounding).
- [ ] Returns `422` for missing or invalid parameters (e.g., `month=13`).
- [ ] Returns `401` if `X-API-Key` is missing or wrong.
- [ ] Returns an empty `groups` array (not an error) when there are no expenses for the month.
- [ ] Integration tests cover: category grouping, payment method grouping, month with no expenses, invalid params, missing auth.

**Frontend:**
- [ ] Pie chart renders on the dashboard with slices matching the API response (correct names, amounts, colours).
- [ ] Month navigator shows the correct current month on first load.
- [ ] Pressing ← moves to the previous month and the chart updates.
- [ ] Pressing → moves to the next month and the chart updates.
- [ ] The → button is disabled when viewing the current month.
- [ ] Switching the group-by toggle updates the chart without a full page reload.
- [ ] URL query params update when the user changes filters, and the correct filters are restored on page refresh.
- [ ] A loading skeleton is shown while data is fetching.
- [ ] An error toast is shown if the API call fails.
- [ ] Empty state message is shown when there are no expenses for the selected month.
- [ ] Chart and controls are fully usable on a 390px wide screen.
- [ ] Arrow buttons have at least 44×44px touch targets.
