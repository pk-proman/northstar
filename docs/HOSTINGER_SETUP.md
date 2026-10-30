# Northstar on Hostinger VPS — current private staging operations

## 1. Scope and safety boundary

This document describes the reconciled staging topology as of 30 October 2026. It is a paper-trading staging deployment, not a production/live trading system.

- Trading mode is `PAPER` and `LIVE_EXECUTION_ENABLED` is `false` in Compose.
- PostgreSQL is private on the Docker `internal` network and has no published host port.
- FastAPI has no published host port; Nginx reaches it as `api:8000` on the `edge` network.
- Nginx serves the frontend on container port `8080`, published on the VPS loopback only as `127.0.0.1:18080`.
- Do not publish port 18080, 8000, 5432 or configure public DNS/reverse proxy until the security gates in this document are complete.
- The application currently has no production authentication/MFA. Treat access as administrator-only through a trusted Mac and SSH tunnel.

Never share SSH passwords, private keys, `.env` contents, broker secrets, tokens, MFA seeds or recovery codes in chat or Git.

## 2. Project and environment files

Expected project path used by the current staging host:

```bash
/root/northstar/northstar-hostinger-kit
```

The runtime file `deploy/.env` is created on the VPS and must not be overwritten during source updates. The tracked `deploy/.env.example` is a template only.

```bash
cd /root/northstar/northstar-hostinger-kit/deploy
cp .env.example .env   # only for a fresh setup; do not run over an existing .env
chmod 600 .env
```

Set a unique strong `POSTGRES_PASSWORD` and review the capital/risk defaults before first startup. Never print the `.env` file or expanded Compose configuration in logs/chat.

## 3. Validate and operate the stack

Run from `/root/northstar/northstar-hostinger-kit`:

```bash
docker compose -f deploy/docker-compose.yml config --quiet
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs --tail=100 api frontend
```

Health checks:

```bash
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/api/v1/system/status
curl -I http://127.0.0.1:18080/
```

Expected health/status responses must show `mode` as `PAPER` and `live_execution_enabled` / `live_execution` as `false`.

Useful commands:

```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f api
docker compose -f deploy/docker-compose.yml restart api
```

Do not use `docker compose down -v`; it deletes the persistent `northstar_pgdata` volume. Avoid recreating the database container during frontend/API-only changes. Back up both source files and database before any schema or deployment migration.

## 4. Access the dashboard privately from Mac

On Mac Terminal, open an SSH tunnel and leave it running:

```bash
ssh -L 18080:127.0.0.1:18080 root@YOUR_VPS_IP
```

Then open `http://127.0.0.1:18080` in the Mac browser. Replace `YOUR_VPS_IP` with the VPS address. The tunnel is the access path; do not expose the frontend port publicly. The API is reached by the browser through same-origin Nginx `/api/` routes, not by publishing port 8000.

## 5. Current frontend/backend boundary

The frontend is not wholly server-backed. Current API-backed operations include order retrieval, portfolio summary, paper-order submission, manual paper exits, risk settings and the paper kill switch. Some research candidates, watchlist/chart behavior, capital-ledger interactions and analytics remain local or illustrative. Do not treat illustrative prices or results as market data or authoritative financial records.

## 6. Broker and market data

No live broker execution, Kite OAuth callback, market-data adapter, validated NSE/BSE instrument master, historical backtest engine or notification worker is implemented in this staging baseline. Do not register a guessed broker callback URL or place real orders. Do not put broker credentials in frontend code, Git, logs or chat. Broker selection and integration require separate API, security, data-rights and regulatory review.

## 7. Production/public-exposure gate

Do not expose Northstar publicly until all of the following are designed, implemented and tested:

- Authentication, MFA, secure sessions, CSRF protection, login throttling and password recovery.
- Role/resource authorization on every private API endpoint.
- Alembic migrations and tested upgrade/rollback procedures.
- Database-level uniqueness, transactional risk/capital reservations and concurrency tests for order submission.
- Append-only audit controls and independently verifiable integrity checkpoints.
- Rate limiting, security headers, secrets management and security review.
- Encrypted off-host backups and successful restore drills with agreed RPO/RTO.
- Operational monitoring, alerting, incident response and access review.
- Applicable broker, exchange, SEBI and data-provider requirements reviewed with qualified parties.

Live execution remains disabled. Any future enablement requires a separate explicit approval and release gate.
