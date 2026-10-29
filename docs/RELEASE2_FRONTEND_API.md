# Northstar Release 2 — frontend/API integration

## What this release changes
- Adds an Nginx frontend container, serving the existing dashboard on VPS loopback port 8080.
- Proxies `/api/*` and `/health` to FastAPI over the private Docker network.
- Dashboard order list, overview positions, paper-order submission, manual paper exits, risk settings and paper kill switch use the backend API.
- API connection status is displayed in the dashboard.
- No live broker order endpoint is added; paper mode remains enforced.

## Important limitations
- This release does **not** yet add authentication or MFA. The API has sensitive unauthenticated routes, including risk settings and the kill switch. Keep ports bound to `127.0.0.1`, access only via SSH tunnel, and do not publish the domain or open these ports publicly.
- Research candidates, the chart, some capital-ledger interactions and portions of analytics remain illustrative/browser-side. Do not treat them as market data or authoritative financial records.
- Release 1 uses `Base.metadata.create_all`; Alembic migrations, robust concurrent idempotency and production-grade audit protection are not part of this package.
- No live market data, Kite OAuth, real broker execution, or notifications are implemented.

## Deploy to existing Hostinger staging
1. Back up the existing project directory and database volume before replacing files.
2. Extract this package on your Mac, then upload the `northstar-hostinger-kit` directory or ZIP to `/root/northstar/`.
3. Ensure the existing `/root/northstar/northstar-hostinger-kit/deploy/.env` is retained. Do not overwrite it with `.env.example`.
4. From `/root/northstar/northstar-hostinger-kit/deploy`, run `docker compose config --quiet`.
5. Run `docker compose up -d --build`.
6. Check `docker compose ps`, `curl -fsS http://127.0.0.1:8000/health`, and `curl -I http://127.0.0.1:8080/`.
7. On your Mac, create a tunnel: `ssh -L 8080:127.0.0.1:8080 root@YOUR_VPS_IP`. Then browse to `http://127.0.0.1:8080`. Keep the tunnel open.

## Rollback
Restore the backed-up frontend and `docker-compose.yml`, then run `docker compose up -d --build`. Do not remove Docker volumes.
