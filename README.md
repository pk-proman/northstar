# Northstar — consolidated Hostinger staging baseline

This repository snapshot is reconciled from the running Hostinger staging source exported on 30 October 2026. It is the agreed development baseline for Northstar. The Mac ZIP previously supplied is retained only as a comparison reference; it is not the source of truth.

## Current architecture

- `backend/` — FastAPI paper-trading API, SQLAlchemy persistence and API tests.
- `frontend/` — existing single-page HTML/JavaScript dashboard. It uses the backend for selected operational workflows and still retains browser-local/illustrative features.
- `deploy/docker-compose.yml` — PostgreSQL, API and Nginx frontend.
- `deploy/nginx.conf` — serves the frontend on container port 8080 and proxies `/api/` and `/health` to FastAPI.
- `deploy/.env.example` — configuration template only; never put real secrets in Git.
- `docs/` — deployment, API integration, security boundaries and release plan.

## Runtime topology

- PostgreSQL is attached only to the private `internal` Docker network and has no published host port.
- FastAPI is attached to `internal` and `edge`; it has no published host port.
- Nginx is attached to `edge` and published only on `127.0.0.1:18080` on the VPS.
- Nginx proxies API calls to `http://api:8000` over the Docker network.
- Trading mode is hard-set to `PAPER`; live execution is hard-disabled in Compose.

Access the UI through an SSH tunnel, not a public reverse proxy. See `docs/HOSTINGER_SETUP.md`.

## Current functional boundary

The dashboard uses the API for order retrieval, portfolio summary, paper-order submission, manual exits, risk settings and the paper kill switch. Some research/watchlist/chart/capital-ledger/analytics behavior remains local or illustrative. Market-data and broker connectivity are not implemented. Do not treat illustrative values as exchange data or trading recommendations.

## Development and verification

Run backend tests from `backend/`:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

Validate deployment configuration from the project root (with a local `deploy/.env` present):

```bash
docker compose -f deploy/docker-compose.yml config --quiet
```

Never commit `deploy/.env`, broker credentials, access tokens, database dumps or runtime data. Do not use `docker compose down -v` on staging; it removes the database volume.

## Security status

**Private staging only — not production-ready.** Authentication, MFA, authorization, CSRF/session protections, database migrations, robust concurrent order/idempotency guarantees, externally verifiable audit integrity, automated off-host backups and restore drills are not complete. Keep the UI bound to loopback and accessible only through a trusted SSH tunnel. Live execution remains disabled.

## Roadmap

See `docs/IMPLEMENTATION_PLAN.md` and `docs/NEXT_RELEASE_PLAN.md` for the phased stabilization-first plan. The agreed frontend direction is to stabilize the existing HTML/JavaScript app first and migrate to React + TypeScript only when the backend contracts and product workflows are sufficiently mature.
