# Northstar Release 2 — frontend/API integration (staging baseline)

## Deployment shape

- Nginx serves the existing dashboard on container port `8080`.
- The VPS publishes the frontend only on `127.0.0.1:18080`.
- Nginx proxies `/api/` and `/health` to FastAPI at `http://api:8000` over Docker network `edge`.
- FastAPI is attached to `edge` and the private `internal` network; it has no host-published port.
- PostgreSQL is attached only to `internal`; it has no host-published port.

The current Compose file uses two networks: `internal` (`internal: true`) for API/database communication and `edge` for frontend/API communication. Do not revert to a single internal-only network: that topology previously prevented Nginx's published frontend port from working on this host.

## API-backed dashboard workflows

The current dashboard uses backend API calls for:

- Order list and portfolio summary refresh.
- Paper-order submission with an `Idempotency-Key` header.
- Manual paper-order exit.
- Risk settings retrieval and update.
- Paper kill-switch state.
- System status and API connection feedback.

## Remaining local/illustrative behavior

Research candidates, watchlist/chart behavior, some capital-ledger interactions and portions of analytics remain local or illustrative. This release does not provide live market data, broker connectivity, real exchange order execution or a validated backtesting engine.

## Security limitations

This release does not provide production authentication/MFA or complete authorization. Some sensitive endpoints (including risk settings and kill switch) must be treated as trusted-admin-only. Keep the frontend loopback-bound and access it only through SSH tunneling. Do not configure public DNS or expose the app to the internet yet.

The backend still uses startup table creation rather than Alembic migrations. Concurrent order idempotency, transaction-level capital/risk reservation and externally verifiable audit integrity require hardening before production use.

## Private access from Mac

```bash
ssh -L 18080:127.0.0.1:18080 root@YOUR_VPS_IP
```

Browse to `http://127.0.0.1:18080` while the tunnel remains open.

## Safe source deployment principles

1. Back up the project source and database before deployment.
2. Preserve the VPS `deploy/.env`; never replace it with `.env.example`.
3. Validate with `docker compose -f deploy/docker-compose.yml config --quiet`.
4. Inspect the planned changes and service status before applying.
5. Never use `docker compose down -v` on staging.
6. Verify `/health`, `/api/v1/system/status` and the frontend after deployment.
