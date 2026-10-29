# Northstar — Hostinger private staging kit

This package provides a conservative, private staging deployment for the existing Northstar Release 1 paper-trading API on Ubuntu 24.04 LTS.

## Contents
- `backend/` — existing Release 1 FastAPI paper backend and tests.
- `frontend/` — existing UX prototype (still browser-local demo state).
- `deploy/docker-compose.yml` — PostgreSQL + API; API bound only to VPS loopback, database unexposed.
- `deploy/.env.example` — required runtime configuration template.
- `scripts/install_docker_ubuntu24.sh` — installs Ubuntu Docker packages.
- `docs/HOSTINGER_SETUP.md` — step-by-step VPS setup and operations.

## Security status
**Staging only. Not production-ready.** No public reverse proxy or public DNS is configured. Access the API through an SSH tunnel. Authentication/MFA, migrations, hardened concurrency, external audit integrity, API-connected frontend, licensed market data, historical backtesting, background workers, monitoring, backup automation and notifications are follow-on implementation work. Live execution is disabled.

See `docs/HOSTINGER_SETUP.md` before running any commands.
