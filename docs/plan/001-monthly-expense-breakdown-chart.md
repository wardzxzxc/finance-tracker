# Implementation Plan: Monthly Expense Breakdown Chart

| Field | Value |
|-------|-------|
| **Plan #** | 001 |
| **Feature PRD** | [docs/features/001-monthly-expense-breakdown-chart.md](../features/001-monthly-expense-breakdown-chart.md) |
| **Status** | Ready to implement |
| **Created** | 2026-03-14 |

---

## Context

This plan covers end-to-end implementation of the monthly expense breakdown pie chart described in the feature PRD. The chart lives on the dashboard, is broken down by category or payment method, and is navigable by month.

### Codebase state at time of writing

The project has a full database schema (models + one migration) and a minimal FastAPI bootstrap, but nothing else is implemented yet:

- **Backend**: `app/models/` complete, `app/db.py` complete, `app/main.py` has only `/health`. Everything else (`schemas/`, `services/`, `api/`) is empty.
- **Frontend**: React + TypeScript + Vite scaffold only. No Tailwind, no shadcn/ui, no React Router, no TanStack Query, no pages, no components, no API client.
- **Tests**: None.

Because this is the first feature being built, several foundational pieces must be created alongside the feature-specific code. This plan covers both.

---

## Implementation Steps

### Step 1 — Backend: Pydantic schemas for the summary endpoint

**File to create:** `backend/app/schemas/summary.py`

Define the following Pydantic v2 models:

```
SummaryQueryParams      — query parameter validation
  month: int            — Field(ge=1, le=12)
  year: int             — Field(ge=1000, le=9999)
  group_by: Literal["category", "payment_method"]

SummaryGroup            — one slice in the response
  id: UUID
  name: str
  color: str            — hex colour, e.g. "#FF6384"
  amount: Decimal       — 2 decimal places
  percentage: float     — 1 decimal place

SummaryResponse         — top-level response body
  month: int
  year: int
  group_by: str
  total: Decimal        — 2 decimal places
  groups: list[SummaryGroup]   — sorted high → low amount; empty list if no data
```

**PRD reference:** §5.1 — full response schema and query parameter table.

---

### Step 2 — Backend: Summary service

**File to create:** `backend/app/services/summary.py`

Create a single async function:

```python
async def get_expense_summary(
    db: AsyncSession,
    month: int,
    year: int,
    group_by: Literal["category", "payment_method"],
) -> SummaryResponse
```

**Logic:**

1. Build a SQLAlchemy query that:
   - Filters `Transaction` rows where `type = 'expense'`.
   - Filters by the given `month` and `year` using `extract('month', Transaction.date)` and `extract('year', Transaction.date)`.
   - Groups by `Transaction.category_id` (if `group_by == "category"`) or `Transaction.payment_method_id` (if `group_by == "payment_method"`).
   - Joins the appropriate table (`Category` or `PaymentMethod`) to fetch `name` and `color`.
   - Aggregates `SUM(Transaction.amount)` per group.

2. Query all categories (or payment methods) to include every group — even those with zero spend in the selected month. Use a LEFT JOIN from the dimension table (`Category` or `PaymentMethod`) to the filtered transaction set, so that groups with no matching transactions appear with `amount = 0`.

3. Calculate `total` as the sum of all group amounts.

4. For each group, calculate `percentage = round(amount / total * 100, 1)`. If `total == 0`, set `percentage = 0.0` for all groups.

5. Sort groups from highest to lowest amount (groups with `amount = 0` appear at the bottom).

6. Return a `SummaryResponse`. If there are no categories/payment methods at all, return `total = 0` and `groups = []`.

**Edge cases to handle:**
- Month with no expense transactions but categories exist → all groups returned with `amount = 0` and `percentage = 0.0`.
- No categories/payment methods in the DB at all → return `groups = []`, `total = 0`.
- Transactions where `payment_method_id` is NULL and `group_by == "payment_method"` → exclude those transactions from the aggregation (NULL payment method transactions don't count toward any group's total).
- Percentage sum may not equal exactly 100 due to rounding; this is acceptable per PRD §8.

**PRD reference:** §5.1 — response field notes, acceptance criteria bullets 1–8.

---

### Step 3 — Backend: Summary API route

**File to create:** `backend/app/api/transactions.py`

Create an `APIRouter` with `prefix="/transactions"` and register one route:

```
GET /transactions/summary
```

Route signature:
```python
@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    params: Annotated[SummaryQueryParams, Query()],
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse
```

- Delegate entirely to `get_expense_summary(db, params.month, params.year, params.group_by)`.
- FastAPI will handle `422` automatically for invalid/missing query parameters via Pydantic validation on `SummaryQueryParams`.
- Do not add any business logic here; the route only validates input, calls the service, and returns.

**PRD reference:** §5.1 — full endpoint specification.

---

### Step 4 — Backend: Register router in main.py

**File to modify:** `backend/app/main.py`

Import the transactions router and register it:

```python
from app.api.transactions import router as transactions_router
app.include_router(transactions_router, prefix="/api")
```

The resulting full path will be `GET /api/transactions/summary`.

---

### Step 5 — Backend: Unit tests for the summary service

**File to create:** `backend/tests/unit/test_summary_service.py`

Use an in-memory fake for the database session (not mocks). Build a `FakeSession` that accepts pre-loaded query results. Test the service function in isolation by injecting controlled data.

**Test cases:**

| # | Test name | Setup | Expected result |
|---|-----------|-------|-----------------|
| 1 | `test_summary_returns_groups_sorted_by_amount_descending` | Two categories with different expense totals for the same month | `groups[0].amount > groups[1].amount` |
| 2 | `test_summary_excludes_income_transactions` | One expense + one income for the same category in the same month | Only expense amount appears in the group total |
| 3 | `test_summary_returns_empty_groups_when_no_expenses` | No transactions for the given month | `groups == []`, `total == 0` |
| 4 | `test_summary_calculates_percentage_correctly` | Two categories: $300 and $700 | Percentages are 30.0 and 70.0 |
| 5 | `test_summary_includes_zero_spend_groups` | Category A has $0 spend, Category B has $500 | Both groups returned; Category A has `amount = 0`, `percentage = 0.0`; Category B is first |
| 6 | `test_summary_groups_by_payment_method` | Two payment methods with different totals | Groups reflect payment method names and IDs |
| 7 | `test_summary_month_boundary` | Transactions in March and April, query for March | Only March expenses returned |
| 8 | `test_summary_percentage_rounds_to_one_decimal` | Three categories with amounts producing non-trivial percentages | Percentages are rounded to one decimal place |

Each test uses its own fixture data; no shared mutable state between tests.

**PRD reference:** §8 acceptance criteria (backend bullets).

---

### Step 6 — Backend: Integration tests for the summary endpoint

**File to create:** `backend/tests/integration/test_summary_endpoint.py`

Use `pytest` + `httpx.AsyncClient` against a real test PostgreSQL database. Provide pytest fixtures that:
- Create a test database session per test.
- Insert seed data (categories, payment methods, transactions) before each test.
- Clean up after each test.

**Test cases:**

| # | Test name | Setup | Expected HTTP + body |
|---|-----------|-------|----------------------|
| 1 | `test_summary_by_category_returns_200` | 2 categories with expense transactions in March 2026 | 200, groups match category names and summed amounts |
| 2 | `test_summary_by_payment_method_returns_200` | 2 payment methods with expense transactions | 200, groups match payment method names |
| 3 | `test_summary_excludes_income` | Mix of income + expense transactions | Income excluded from totals |
| 4 | `test_summary_empty_month_returns_empty_groups` | No transactions in queried month | 200, `groups == []`, `total == 0` |
| 5 | `test_summary_groups_sorted_high_to_low` | Categories with different spend amounts | Response `groups` are in descending amount order |
| 6 | `test_summary_missing_month_param_returns_422` | No `month` query param | 422 |
| 7 | `test_summary_invalid_month_value_returns_422` | `month=13` | 422 |
| 8 | `test_summary_invalid_group_by_returns_422` | `group_by=foobar` | 422 |
| 9 | `test_summary_percentage_sums_approximately_100` | Multiple categories | Sum of `percentage` values ≈ 100 (within rounding tolerance) |

**PRD reference:** §8 acceptance criteria (backend bullets).

---

### Step 7 — Frontend: Install missing dependencies

**File to modify:** `frontend/package.json` (via `npm install`)

The current `package.json` only has React + TypeScript + Vite. Add:

```
npm install tailwindcss @tailwindcss/vite
npm install react-router-dom
npm install @tanstack/react-query
npm install recharts
npm install date-fns
npm install motion
npm install -D @types/recharts
```

Also install shadcn/ui via CLI:
```
npx shadcn@latest init
```

After init, add the specific shadcn/ui components needed:
```
npx shadcn@latest add button toggle-group card skeleton
```

Set up Tailwind by adding `@tailwind` directives to `src/index.css` and configuring `tailwind.config.js` to scan `./src/**/*.{ts,tsx}`.

---

### Step 8 — Frontend: Design system & theme

**Files to create:** `frontend/src/styles/theme.css` (imported into `src/index.css`)

This is foundational — establish the full visual identity before building any components. Every subsequent component inherits from these decisions.

**Typography**

Choose a font pairing that feels distinctive for a personal finance app. Avoid Inter, Roboto, Arial, system-ui, and Space Grotesk — these are the defaults every AI reaches for. Think instead about:
- A display/heading font with personality: geometric with optical quirks, a humanist sans with unusual weight distribution, or a sharp modern serif
- A body font that is highly legible at small sizes but still has character

Load the chosen fonts via Google Fonts or a self-hosted `@font-face` in `theme.css`. Set them as CSS variables:
```css
--font-heading: 'ChosenHeadingFont', sans-serif;
--font-body: 'ChosenBodyFont', sans-serif;
```

Apply globally in `index.css`: `body { font-family: var(--font-body); }`.

**Color palette**

Commit to a cohesive dark or light theme. Define all colors as CSS variables — nothing hardcoded in component files. Think outside the standard palette:
- Draw from IDE themes (Dracula, Catppuccin, Rosé Pine), film aesthetics, or cultural references
- Dominant background + strong accent, not a spread of equally-weighted pastels
- Avoid purple-on-white, the most overused AI-generated palette

Example variable structure:
```css
:root {
  --color-bg:        /* page background */
  --color-surface:   /* card/panel backgrounds */
  --color-border:    /* subtle borders */
  --color-text:      /* primary text */
  --color-muted:     /* secondary/label text */
  --color-accent:    /* primary interactive color */
  --color-accent-fg: /* text on accent */
}
```

**Background**

Do not use a flat solid background. Layer 2–3 CSS gradients or add a subtle geometric pattern (e.g. a CSS dot grid, diagonal lines, or a radial glow from one corner) that gives the page atmosphere. This should be applied to the `body` or root layout element, not individual components.

**Motion defaults**

Define CSS custom properties for animation timing that all components will reuse:
```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--duration-fast: 150ms;
--duration-base: 280ms;
--duration-slow: 500ms;
```

**CLAUDE.md reference:** Visual Design — Typography, Color & Theme, Backgrounds & Depth.

---

### Step 9 — Frontend: Bootstrap providers in main.tsx

**File to modify:** `frontend/src/main.tsx`

Wrap the application in:
1. `BrowserRouter` from `react-router-dom` — enables React Router v6.
2. `QueryClientProvider` from `@tanstack/react-query` with a `QueryClient` instance — enables TanStack Query throughout the app.

Import `src/styles/theme.css` here (or in `index.css`) so variables are available globally.

---

### Step 10 — Frontend: App routing

**File to modify:** `frontend/src/App.tsx`

Replace the current proof-of-concept with a React Router `Routes` setup:

```tsx
<Routes>
  <Route path="/" element={<Navigate to="/dashboard" replace />} />
  <Route path="/dashboard" element={<DashboardPage />} />
</Routes>
```

Remove the direct `fetch` call from `App.tsx`.

---

### Step 11 — Frontend: Typed API client function

**File to create:** `frontend/src/api/summary.ts`

Define TypeScript types matching the backend response schema:

```ts
type GroupBy = "category" | "payment_method";

interface SummaryGroup {
  id: string;
  name: string;
  color: string;
  amount: number;
  percentage: number;
}

interface SummaryResponse {
  month: number;
  year: number;
  group_by: GroupBy;
  total: number;
  groups: SummaryGroup[];
}
```

Export a typed async function:

```ts
async function getExpenseSummary(
  month: number,
  year: number,
  groupBy: GroupBy,
): Promise<SummaryResponse>
```

- Use the native `fetch` API.
- Read `VITE_API_BASE_URL` from `import.meta.env` (falls back to `/api` if not set).
- Throw an error on non-2xx responses so TanStack Query can treat it as a failed query.

---

### Step 12 — Frontend: DashboardPage

**File to create:** `frontend/src/pages/DashboardPage.tsx`

A page-level component that renders the dashboard layout. Initially it contains only `<ExpenseBreakdownChart />`. Future sections (transaction list, budget bars) will be added here later.

**Page load animation:** Use Motion (`motion/react`) to orchestrate a staggered entrance for the page content. The chart section should fade and slide up on mount with a short delay — one well-composed entrance animation, not scattered micro-interactions on every element. Use the `--duration-slow` and `--ease-out` CSS variables (or their Motion equivalents) for timing.

---

### Step 13 — Frontend: ExpenseBreakdownChart (owner component)

**File to create:** `frontend/src/components/charts/ExpenseBreakdownChart.tsx`

This component owns:
- **Filter state**: selected `year`/`month` (derived from URL or defaulting to current month) and `groupBy` (from URL or defaulting to `"category"`).
- **URL sync**: reads initial state from `useSearchParams()` on mount; calls `setSearchParams` on every filter change (React Router's equivalent of `history.replaceState`). If URL params are missing or invalid, fall back to defaults.
- **Data fetching**: `useQuery({ queryKey: ['expense-summary', year, month, groupBy], queryFn: () => getExpenseSummary(month, year, groupBy) })`.
- **Rendering**: composes `MonthNavigator`, `GroupByToggle`, and `PieChartDisplay` (or empty state).

**Layout:**
- Mobile (`< 768px`): controls stack vertically (MonthNavigator on top, GroupByToggle below, chart below that, legend below chart).
- Desktop (`≥ 768px`): MonthNavigator and GroupByToggle side by side above the chart; legend to the right.
- Use Tailwind responsive prefixes for this.

**States to handle:**
- `isLoading` → render `<ChartSkeleton />` (themed placeholder, same dimensions as chart area).
- `isError` → show toast "Failed to load expense summary. Please try again."
- `data.groups.length === 0` → show empty state message.
- Otherwise → render `<PieChartDisplay />`.

**Styling:** All colors from CSS variables (`var(--color-surface)`, etc.), not hardcoded Tailwind color classes. The component container should use `var(--color-surface)` for its background and `var(--color-border)` for any borders.

**PRD reference:** §6.2, §6.3, §6.4, §6.5.

---

### Step 14 — Frontend: MonthNavigator component

**File to create:** `frontend/src/components/charts/MonthNavigator.tsx`

Presentational component. Props:
```ts
interface MonthNavigatorProps {
  year: number;
  month: number;                // 1-indexed
  onPrev: () => void;
  onNext: () => void;
  isNextDisabled: boolean;      // true when viewing current month
}
```

Renders:
```
← | March 2026 | →
```

- Format the label using `date-fns`: `format(new Date(year, month - 1), "MMMM yyyy")`.
- Left arrow (`←`) button always enabled.
- Right arrow (`→`) button disabled (visually greyed out, `aria-disabled`) when `isNextDisabled` is true.
- Both buttons must have a minimum touch target of 44×44px (use `min-h-[44px] min-w-[44px]` Tailwind classes).
- **Styling:** The month label uses `var(--font-heading)` and is set larger than surrounding body text. Arrow buttons use `var(--color-accent)` for their active color. No generic shadcn button defaults — style these to match the theme.
- **Micro-interaction:** Add a brief CSS transition on the month label when it changes (fade out/in or slide) so the month switch feels responsive rather than instant. Keep it under `var(--duration-fast)`.

In `ExpenseBreakdownChart`, `isNextDisabled` is computed as:
```ts
const now = new Date();
isNextDisabled = year === now.getFullYear() && month === now.getMonth() + 1;
```

**PRD reference:** §4.2.

---

### Step 15 — Frontend: GroupByToggle component

**File to create:** `frontend/src/components/charts/GroupByToggle.tsx`

Presentational component. Props:
```ts
interface GroupByToggleProps {
  value: "category" | "payment_method";
  onChange: (value: "category" | "payment_method") => void;
}
```

Renders a segmented control (shadcn/ui `ToggleGroup`) with two options:
- "Category" (value: `"category"`)
- "Payment Method" (value: `"payment_method"`)

The currently selected option is visually highlighted.

**Styling:** Override the default shadcn/ui `ToggleGroup` styles to use `var(--color-accent)` for the selected state and `var(--color-surface)` for the background. The toggle should feel like it belongs to the same design system as the rest of the page, not like a lifted-from-docs component.

**PRD reference:** §4.3.

---

### Step 16 — Frontend: PieChartDisplay component

**File to create:** `frontend/src/components/charts/PieChartDisplay.tsx`

Presentational component. Props:
```ts
interface PieChartDisplayProps {
  groups: SummaryGroup[];
  total: number;
}
```

Renders a Recharts `PieChart`:
- Each entry in `groups` becomes one pie slice. Slice colour comes from `group.color`.
- **Slice entrance animation:** Use Recharts' built-in `isAnimationActive` with a custom `animationBegin` / `animationDuration`, or override with Motion to animate slices fading and scaling in from the centre on first render. The animation should feel satisfying, not distracting — a single sweep, not bouncing.
- **Labels:** Use a custom `renderCustomizedLabel` to show `"{name} · ${amount}"` outside small slices and inside larger ones. Label text uses `var(--font-body)` and `var(--color-text)`.
- **Tooltip:** Implement a fully custom `<Tooltip content={...}>` component styled with `var(--color-surface)`, `var(--color-border)`, and `var(--font-body)` — do not use the default Recharts tooltip appearance. It shows:
  ```
  {name} — ${amount.toFixed(2)} — {percentage}%
  ```
- Use `ResponsiveContainer` with `width="100%"`.
- **Legend:** Render a custom legend (not the Recharts default `<Legend />`): a simple list of coloured dots + group names + amounts, styled in `var(--color-text)` / `var(--color-muted)`. On mobile it appears below the chart, on desktop it is positioned to the right (the parent component controls the layout container).

**PRD reference:** §4.1.

---

### Step 17 — Frontend: Loading skeleton

**File to create:** `frontend/src/components/charts/ChartSkeleton.tsx`

Renders a placeholder matching the approximate dimensions of the chart area, shown while `isLoading` is true.

**Styling:** Use shadcn/ui `Skeleton` as the base but override its background to use `var(--color-surface)` with a shimmer animation that uses `var(--color-border)` — so the skeleton matches the page theme rather than being a generic grey rectangle. The shimmer direction and speed should feel intentional: a slow diagonal sweep looks more polished than the default horizontal flash.

**PRD reference:** §6.3 — "show a loading skeleton … do not show a spinner over the old chart."

---

## File Map

The table below lists every file that must be created or modified.

| # | File | Action |
|---|------|--------|
| 1 | `backend/app/schemas/summary.py` | Create |
| 2 | `backend/app/schemas/__init__.py` | Create (empty, or re-export) |
| 3 | `backend/app/services/summary.py` | Create |
| 4 | `backend/app/services/__init__.py` | Create (empty) |
| 5 | `backend/app/api/transactions.py` | Create |
| 6 | `backend/app/api/__init__.py` | Create (empty) |
| 7 | `backend/app/main.py` | Modify (register router) |
| 8 | `backend/tests/unit/test_summary_service.py` | Create |
| 9 | `backend/tests/unit/conftest.py` | Create (shared unit test fixtures) |
| 10 | `backend/tests/integration/test_summary_endpoint.py` | Create |
| 11 | `backend/tests/integration/conftest.py` | Create (DB setup/teardown fixtures) |
| 12 | `frontend/package.json` | Modify (add deps including `motion`) |
| 13 | `frontend/src/styles/theme.css` | Create (CSS variables, fonts, background) |
| 14 | `frontend/src/index.css` | Modify (import theme.css, apply font/background globals) |
| 15 | `frontend/src/main.tsx` | Modify (add providers) |
| 16 | `frontend/src/App.tsx` | Modify (add routing) |
| 17 | `frontend/src/api/summary.ts` | Create |
| 18 | `frontend/src/pages/DashboardPage.tsx` | Create |
| 19 | `frontend/src/components/charts/ExpenseBreakdownChart.tsx` | Create |
| 20 | `frontend/src/components/charts/MonthNavigator.tsx` | Create |
| 21 | `frontend/src/components/charts/GroupByToggle.tsx` | Create |
| 22 | `frontend/src/components/charts/PieChartDisplay.tsx` | Create |
| 23 | `frontend/src/components/charts/ChartSkeleton.tsx` | Create |

---

## Acceptance Criteria Mapping

Each item from the PRD §8 acceptance checklist maps to a specific implementation step and test.

### Backend

| PRD Criterion | Covered by |
|---------------|------------|
| Category grouping returns correct totals | Step 2 service logic; Integration test #1 |
| Payment method grouping returns correct totals | Step 2 service logic; Integration test #2 |
| Income excluded from all totals | Step 2 service logic; Unit test #2; Integration test #3 |
| Zero-spend groups included (with `amount = 0`) | Step 2 service logic; Unit test #5 |
| Groups sorted high → low | Step 2 service logic; Unit test #1; Integration test #5 |
| Percentages sum to ~100% | Step 1 schema + Step 2 logic; Unit test #8; Integration test #9 |
| 422 for missing/invalid params | Step 1 schema validation (Pydantic); Integration tests #6, #7, #8 |
| Empty groups (no expenses) returns 200 not error | Step 2 service logic; Unit test #3; Integration test #4 |
| Integration tests cover all cases above | Steps 5–6 |

### Frontend

| PRD Criterion | Covered by |
|---------------|------------|
| Pie chart renders with correct slices | Step 16 PieChartDisplay |
| Month navigator shows current month on load | Step 13 ExpenseBreakdownChart (default state) |
| ← moves to previous month | Step 14 MonthNavigator + Step 13 handler |
| → moves to next month | Step 14 MonthNavigator + Step 13 handler |
| → disabled on current month | Step 14 MonthNavigator props + Step 13 computation |
| Group-by toggle updates chart without reload | Step 15 GroupByToggle + Step 13 state update |
| URL params update on filter change; restored on refresh | Step 13 URL sync via `useSearchParams` |
| Loading skeleton shown while fetching | Step 17 ChartSkeleton; Step 13 isLoading branch |
| Error toast on API failure | Step 13 isError branch |
| Empty state message when no expenses | Step 13 empty groups branch |
| Usable on 390px screen | Step 13 responsive layout (Tailwind mobile-first) |
| Touch targets ≥ 44×44px | Step 14 MonthNavigator button sizing |

### Visual Design

| Criterion | Covered by |
|-----------|------------|
| Distinctive font pairing (no Inter/Roboto/Space Grotesk) | Step 8 theme.css |
| Full palette defined as CSS variables | Step 8 theme.css |
| Atmospheric background (not solid color) | Step 8 theme.css applied in Step 12 DashboardPage |
| Motion library installed and used for page entrance | Steps 7 (dep) + 12 (DashboardPage stagger) |
| Pie chart entrance animation | Step 16 PieChartDisplay |
| Month label transition on navigation | Step 14 MonthNavigator |
| Themed skeleton (not generic grey) | Step 17 ChartSkeleton |
| Custom tooltip matching design system | Step 16 PieChartDisplay |
| All component colors via CSS variables | Steps 13–17 |

---

## Implementation Order

Follow this order to minimise integration gaps. Red-Green-Refactor within each step (write test first, then implement).

```
1  → schemas/summary.py                 (unblocks service + route)
2  → services/summary.py                (core logic)
3  → api/transactions.py                (wires route to service)
4  → main.py update                     (endpoint live)
5  → unit tests                         (service tested in isolation)
6  → integration tests                  (full stack verified)
7  → frontend deps (incl. motion)       (unblocks all frontend work)
8  → theme.css + index.css              (design system established before any component)
9  → main.tsx, App.tsx                  (routing + providers live)
10 → api/summary.ts                     (typed client)
11 → DashboardPage                      (page shell + entrance animation)
12 → MonthNavigator, GroupByToggle      (presentational controls, themed)
13 → PieChartDisplay, ChartSkeleton     (chart display + animations)
14 → ExpenseBreakdownChart              (everything wired together)
```
