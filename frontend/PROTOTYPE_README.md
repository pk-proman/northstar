# Northstar Automated Trading Platform — Prototype

## What this is
A responsive, single-page front-end prototype for an India NSE/BSE paper-trading control tower. It includes dashboard navigation, illustrative research candidates, local paper positions, simulated exits, a capital ledger, risk-limit settings, date-range trade analytics and CSV exports.

## Important limitations
- This is a front-end prototype, not a production trading application.
- All quotes, scores, performance metrics and closed trades are synthetic demo data.
- Data changes are stored in the browser's localStorage and are not shared with a server.
- No authentication, backend, PostgreSQL, live market data, broker connection or actual exchange order execution is included.
- The paper order flow is for UX demonstration only; its price/fill simulation is not a validated backtesting engine.
- Live trading is not implemented and must not be enabled without broker-specific implementation, regulatory/compliance validation, operational controls and security testing.

## Run the prototype
Open `index.html` in a modern browser. No build step or external dependency is required. For PWA/local web-server testing, run a local static server from this folder, e.g. `python -m http.server 8080`, then open `http://localhost:8080`.

## Planned production architecture
- Frontend: Next.js / React / TypeScript, installable PWA.
- Backend: FastAPI, PostgreSQL, Redis + durable task queue.
- Separate workers for market data, strategy evaluation, paper simulator, broker sync and analytics.
- Broker adapters must be isolated behind a strict interface.
- Separate paper and live environments; no live credentials in paper runtime.
- Every order requires deterministic risk authorization and an immutable audit trail.

## Suggested next milestone
Turn the UX into a tested application with server-side authentication, PostgreSQL schema/migrations, paper engine, market-data adapter and automated acceptance tests. Select broker only after reviewing API access, data rights, static-IP rules, order limits and current Indian retail algo requirements.
