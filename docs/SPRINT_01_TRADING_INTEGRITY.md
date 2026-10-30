# Northstar Sprint 01 — Trading Integrity

## Scope

This sprint hardens the existing paper-trading backend without enabling live trading or changing the Hostinger deployment.

## Implemented

1. **Payload-bound idempotency**
   - Stores a SHA-256 fingerprint for each accepted idempotency key in a dedicated `idempotency_records` table.
   - Repeating the same key and same payload returns the original order.
   - Reusing the key with a different payload returns HTTP 409.
   - Unique database constraints and integrity-error recovery protect the create path against duplicate-key races.
   - Legacy orders without a fingerprint record are compared field-by-field for compatibility.

2. **Serialized risk evaluation**
   - Paper-order risk checks lock the singleton risk-settings row with `SELECT ... FOR UPDATE`.
   - On PostgreSQL this serializes concurrent order authorization so each request evaluates after the prior transaction commits.
   - SQLite does not enforce row-level `FOR UPDATE`; SQLite is used only for the local automated test suite.

3. **Emergency-stop separation**
   - `RiskSettingsUpdate` no longer accepts `halted` as a writable setting.
   - Legacy clients may still send the field, but it is ignored; only the dedicated kill-switch endpoint changes halt state.
   - The frontend label now describes the backend-wide paper-entry halt rather than a browser-local block.

4. **Exit serialization**
   - Exit requests lock the target order row on databases supporting row-level locks.
   - A second exit request for an already-closed order returns HTTP 409.

5. **Exchange-specific latest quotes**
   - Latest-quote lookup accepts an exchange (NSE by default) and filters by both instrument and exchange.

6. **FastAPI lifespan**
   - Replaced deprecated startup event registration with a lifespan handler.

## Database behavior

The new `idempotency_records` table is added through the existing SQLAlchemy `Base.metadata.create_all()` startup behavior. Existing tables and records are not altered by this sprint. This is a narrow compatibility step, not a substitute for the planned Alembic migration framework.

## Verification

Automated backend tests: **10 passed**.

New regression tests cover:
- Same idempotency key with changed payload returns 409.
- Saving risk settings cannot clear an active emergency halt.
- Latest quote selection is exchange-specific.
- A closed paper order cannot be exited a second time.

## Explicit limitations

- Authentication, MFA and authorization are not implemented by this sprint. Keep the application private; do not expose the API publicly.
- PostgreSQL concurrency behavior must still be stress-tested on the Hostinger staging database before relying on it for concurrent workloads.
- SQLite tests validate functional behavior but cannot prove PostgreSQL row-lock semantics.
- Live broker execution remains absent and disabled. This remains a paper-trading system.
