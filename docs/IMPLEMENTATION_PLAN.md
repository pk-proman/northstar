# Northstar — consolidated implementation plan

**Baseline:** Hostinger staging source export, 30 October 2026.  
**Frontend direction:** phased approach — stabilize the existing HTML/JavaScript application first; evaluate React + TypeScript migration after API contracts and workflows are mature.  
**Trading safety:** paper-only; live execution remains disabled.

## Guiding principles

1. Preserve working staging behavior; do not rewrite for fashion.
2. Mac is the development workstation; GitHub is the source of truth; Hostinger is staging.
3. Every release is built and tested from a Git commit, not edited ad hoc on the VPS.
4. Backend services own financial state, risk decisions, order lifecycle and audit events.
5. Browser-local state may hold presentation preferences, never authoritative capital, orders, fills or risk state.
6. No live execution until separate security, operational, broker and compliance gates are approved.

## Baseline findings

- FastAPI, SQLAlchemy and PostgreSQL-backed paper API are present.
- The current dashboard calls the API for orders, portfolio summary, paper order entry, manual exits, risk settings, kill switch and system status.
- Some watchlist/research/chart/capital-ledger/analytics features remain local or illustrative.
- Existing backend tests: 6 passed in the supplied staging source; FastAPI startup event API emits deprecation warnings.
- No authentication/MFA, complete authorization, Alembic migrations, robust concurrency-safe order idempotency, external audit integrity, market data adapter, instrument master, historical backtester, durable worker or broker adapter.
- Current Hostinger topology is verified: DB on `internal`; API on `internal` + `edge`; frontend on `edge`; only frontend published on `127.0.0.1:18080`.

## Workstream 0 — baseline and release discipline

### Tasks
- Adopt this staging export as the baseline; reconcile into Mac working tree and GitHub.
- Keep secrets and VPS `.env` outside Git.
- Add repeatable local test and Compose validation instructions.
- Tag the reconciled baseline commit after verification.
- Create a release checklist and a staging backup/rollback procedure.

### Acceptance
- Git working tree clean after baseline commit.
- No secrets, cache files, database files or `.git` internals in source archive.
- Backend test suite passes; Compose config validates with local environment configured.
- Mac/GitHub baseline matches the approved staging source.

## Workstream 1 — operational dashboard stabilization

### Tasks
- Centralize API client behavior, request timeout, error normalization and API status.
- Make refresh deterministic; avoid stale UI state and duplicate event handlers.
- Make API-backed values clearly authoritative and local/illustrative panels explicitly labeled.
- Move authoritative capital ledger and portfolio calculations to backend endpoints.
- Persist watchlists and strategy configuration server-side after authentication/ownership model exists.
- Add frontend tests for order submission, exits, risk settings, kill switch, empty states and API failures.
- Correct currency precision display; show fees and small P&L values without rounding them to zero.

### Acceptance
- Reloading the browser does not lose backend-backed orders, risk or portfolio state.
- API outage is clearly indicated; stale/sample data is not presented as live.
- Duplicate clicks/retries do not create duplicate paper orders.
- Every UI action has success/failure feedback and a corresponding backend result.

## Workstream 2 — security and persistence foundation (must precede public access)

### Tasks
- Define user, role and resource ownership model.
- Password hashing, login throttling, secure server-side sessions, CSRF protection, logout and password reset.
- TOTP MFA with hashed single-use recovery codes and audited reset flow.
- Authorization dependencies on every private endpoint; restrict risk administration and kill switch.
- Add Alembic migrations; replace production startup `create_all` behavior with controlled migration execution.
- Enforce order idempotency with a unique database constraint and payload fingerprint; same key + same payload returns same result, same key + different payload returns conflict.
- Use database transactions/locking or equivalent concurrency-safe reservations for capital, open-position and risk limits.
- Add audit event sequence/hash and periodic off-host integrity checkpoint.

### Acceptance
- Anonymous requests cannot read or mutate private account data.
- Authorization tests cover every route and role.
- Concurrent duplicate order submissions create exactly one order.
- Concurrent distinct orders cannot exceed capital, daily-loss or open-position limits.
- Migration upgrade and restore tested on a database copy.
- Audit modification is detectable.

## Workstream 3 — market/reference data

### Tasks
- Define provider-neutral quote and historical candle interfaces.
- Instrument master import/versioning for NSE/BSE with exchange, token, symbol, tick size, lot size and active status.
- Exchange calendar, holidays and special sessions.
- Record provider timestamp, receive timestamp, source and freshness.
- Validate malformed, stale, out-of-session and out-of-order data.
- Select data vendor/broker only after reviewing API terms, data rights, rate limits and cost.

### Acceptance
- Invalid/stale quotes are rejected and visibly flagged.
- Exchange and instrument identity are unambiguous.
- Reconnect, gaps, delayed data and provider outage are tested.
- Data rights and retention terms documented.

## Workstream 4 — research and backtesting

### Tasks
- Versioned strategy definitions and parameters.
- Event-driven historical simulator with brokerage, taxes/charges, slippage, gaps, partial fills and corporate actions.
- Deterministic datasets/runs; persist strategy version, data version and assumptions.
- Out-of-sample, walk-forward and sensitivity analysis; prevent look-ahead and survivorship bias.

### Acceptance
- Identical inputs produce deterministic results.
- Fixtures cover gap-through-stop, partial fills, session boundaries, charges and missing data.
- No future bars are visible to a strategy decision.
- Backtest assumptions are visible alongside performance metrics.

## Workstream 5 — automated paper execution

### Tasks
- Durable worker/queue with retries, backoff, dead-letter handling and idempotent jobs.
- Signal-to-order state machine and server-side risk authorization.
- Order lifecycle reconciliation, partial fills, cancel/replace simulation and position accounting.
- Stop-loss/target monitoring, daily loss halt, max positions, reserve and kill switch.
- Structured logs, metrics, alerting and operational dashboards.

### Acceptance
- Worker restart does not lose or duplicate jobs.
- Every order transition is auditable and reconciled.
- Kill switch prevents new entries while allowing defined safe exit/administrative actions.
- Fault injection and recovery tests pass.

## Workstream 6 — React migration decision

Do not migrate immediately. First stabilize workflows, define OpenAPI contracts, and complete API-backed state ownership. Then evaluate React + TypeScript based on component complexity, testability, maintainability and user experience needs. If approved, migrate module-by-module while preserving API contracts and visual parity; do not run two competing sources of financial state.

## Workstream 7 — broker/live readiness (separate approval gate)

- Broker adapter and OAuth callback over HTTPS; secrets server-side only.
- Read-only account/position sync before any order capability.
- Static egress IP, rate limits, order reconciliation, kill switch and per-order risk gate.
- Review applicable SEBI, exchange, broker and data-provider requirements with qualified parties.
- Paper/sandbox/dry-run validation and explicit operational approval.
- Live execution remains feature-flagged off until written sign-off; no live code path is to be enabled as part of the current roadmap.

## Immediate next sprint

1. Reconcile baseline into Mac and GitHub.
2. Fix documentation and add clean `.gitignore`.
3. Add backend tests for idempotency payload mismatch, concurrent order placement, capital reservation and daily loss boundary.
4. Add API contract tests for all frontend-consumed endpoints.
5. Refactor frontend API client and make API-backed vs illustrative panels unmistakable.
6. Design security model and Alembic migration plan before implementation.
