# Northstar next releases and acceptance gates

## R2A — Secure application foundation
1. Replace localStorage as the source of truth with API-backed frontend state and explicit loading/error states.
2. Add user model, password hashing, login throttling, secure server-side sessions, CSRF protection, password reset, TOTP MFA and hashed single-use recovery codes.
3. Add resource ownership and role authorization to every non-public API endpoint.
4. Introduce Alembic migrations and migration tests; stop using create_all in production.
5. Enforce order idempotency with unique constraints and transactional risk/capital reservation; add concurrent submission tests.
6. Make audit records append-only at application level, add event hashes and periodic off-host integrity checkpoints.

Acceptance: unauthenticated requests cannot read or mutate private data; MFA reset audited; repeated idempotency keys produce one order; concurrent order tests cannot breach limits; migration upgrade tested on a copy; audit tampering detectable.

## R2B — Market data and exchange reference data
- Implement provider interface for Kite WebSocket quotes and historical candles.
- Persist data provenance, provider timestamps, receive timestamps and freshness status.
- Import/version instrument master; validate exchange, symbol/token, tick size, lot size and active status.
- Add NSE/BSE session calendar and holiday/special-session updates.
- Confirm licensing and retention rights before historical bulk storage or redistribution.

Acceptance: stale/out-of-session/malformed quotes rejected; tick-size violations blocked; reconnect and missing-data behavior tested; provider terms documented.

## R2C — Backtesting
- Event-driven historical simulator with deterministic runs, transaction costs, slippage and corporate actions.
- Avoid look-ahead and survivorship bias; use out-of-sample and walk-forward validation.
- Save strategy version, parameters, dataset version and execution assumptions with every result.

Acceptance: deterministic repeat runs; unit fixtures for gaps, partial fills, stops/targets, costs and session boundaries; no future bars exposed to a decision.

## R2D — Operations and notifications
- Durable task queue, retry/backoff, dead-letter queue and idempotent jobs.
- Health checks, structured logs, metrics, alerts and error tracking.
- Email via Microsoft Graph or approved SMTP service; WhatsApp via official Cloud API/approved provider with opt-in and template compliance.
- Encrypted offsite backups and timed restore drills.

Acceptance: worker restart does not lose jobs; duplicate jobs do not duplicate actions; alerts arrive on synthetic test events; restore drill meets agreed RPO/RTO.

## R3 — Broker integration and compliance gate
- OAuth callback over HTTPS, server-side secrets and daily token lifecycle handling.
- Read-only account/data integration first, then sandbox/dry-run order adapter.
- Explicit per-order risk gate, static-IP egress validation, rate limiting, order reconciliation and kill switch.
- Review latest SEBI, NSE/BSE, broker and data-provider requirements with the relevant parties.
- Live order execution remains feature-flagged off until written approval and acceptance tests.
