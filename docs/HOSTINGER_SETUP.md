# Northstar on Hostinger VPS — private staging setup

## Safety boundary
This kit deploys the Release 1 **paper-only** API and stores PostgreSQL privately. It does **not** provide production authentication/MFA, migrations, broker execution, or the API-connected frontend. Do not expose port 8000 publicly or configure a public reverse proxy yet. The UI in `frontend/index.html` is still a demo using browser `localStorage`; it is not yet connected to the API.

## 0. Before running commands
- Confirm Hostinger VPS is Ubuntu 24.04 LTS and you can SSH in.
- Keep your VPS SSH session open while changing firewall rules.
- Do not send SSH credentials, broker API secret, Microsoft 365 credentials, TOTP seeds, or recovery codes in chat.
- The VPS public IPv4 is the candidate Zerodha static IP. Verify with `curl -4 https://api.ipify.org` from the VPS and compare with Hostinger hPanel. Do not whitelist until confident the outbound route is stable.

## 1. Upload and extract the kit
On your Mac, upload `Northstar_Hostinger_Deployment_Kit.zip` to your home directory using your preferred SFTP client. Then SSH into the VPS and run:

```bash
sudo apt-get update && sudo apt-get install -y unzip
mkdir -p ~/northstar && cd ~/northstar
unzip ~/Northstar_Hostinger_Deployment_Kit.zip
```

If you uploaded to another path, adjust the unzip path. Expected directory: `northstar-hostinger-kit/`.

## 2. Install Docker
From the extracted kit directory:

```bash
cd ~/northstar/northstar-hostinger-kit
bash scripts/install_docker_ubuntu24.sh
```

## 3. Create secrets and environment file

```bash
cd ~/northstar/northstar-hostinger-kit/deploy
cp .env.example .env
openssl rand -hex 32
nano .env
```

Replace `POSTGRES_PASSWORD` with the generated random value (do not reuse any account password). Save and exit. Then:

```bash
chmod 600 .env
```

Do not paste the secret into chat or commit `.env` to source control.

## 4. Start the paper API

```bash
cd ~/northstar/northstar-hostinger-kit/deploy
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs --tail=100 api
```

The API is bound to `127.0.0.1:8000` on the VPS only; PostgreSQL has no published host port. Live execution is explicitly disabled. Verify on the VPS:

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected JSON should identify PAPER mode and `live_execution_enabled` as false.

## 5. Test privately from your Mac
Open a new Terminal window on your Mac (keep this tunnel open):

```bash
ssh -L 8000:127.0.0.1:8000 YOUR_SSH_USER@YOUR_VPS_PUBLIC_IP
```

Replace the placeholders with your actual SSH username and VPS IP. Then open `http://127.0.0.1:8000/docs` on your Mac. This uses an SSH tunnel; the API port is not public. The API currently has no application authentication, so treat this as a temporary administrator-only staging tunnel on a trusted Mac. Do not share the tunnel or use it from an untrusted device.

## 6. Basic operational commands

```bash
# Status
sudo docker compose ps

# Logs
sudo docker compose logs -f api

# Restart API
sudo docker compose restart api

# Stop services (database data volume remains)
sudo docker compose down

# Start again
sudo docker compose up -d
```

Avoid `docker compose down -v`; it deletes the persistent database volume.

## 7. Zerodha Kite Connect setup
- Use the VPS static outbound IPv4 as the candidate IP for the Kite Connect developer profile's IP whitelist for order placement. Confirm the current rules in Zerodha's console; IP changes may be restricted.
- Redirect URL must be the exact HTTPS callback implemented in Northstar. Do not register a guessed callback route. This kit does not yet implement the Kite OAuth callback.
- Do not add API key/secret or access tokens to frontend HTML, Git, logs, or chat. Store them in a server-side secret store only after the broker integration is implemented.
- Kite access tokens expire daily; implement a deliberate user-driven login/session refresh flow rather than assuming permanent access.
- Live execution remains disabled; do not test by placing real orders.

## 8. Domain and HTTPS — defer public exposure
The domain is not configured yet. Before opening Northstar to the public internet, complete authentication + MFA, authorization, CSRF/session protection, rate limits, Alembic migrations, security headers, audit protections, backups/restore tests, and a security review. After that, configure DNS and TLS and expose only the web entrypoint through a reverse proxy. Never publish PostgreSQL or the internal API port directly.

## 9. Email and WhatsApp
### Microsoft 365 email
Create a dedicated sender mailbox or approved SMTP/Graph sending identity, then configure server-side credentials in a secret manager/environment. Prefer Microsoft Graph with least-privilege permissions and administrator consent where appropriate. Do not use a personal mailbox password or bypass MFA with a shared password.

### WhatsApp
Use the official WhatsApp Business Platform Cloud API or an approved provider. You will need a Meta Business portfolio, a WhatsApp Business Account, a dedicated/eligible phone number, an app, a token stored server-side, and approved message templates for business-initiated notifications. Obtain recipient opt-in and honor opt-outs. Start with a test number and template; never put tokens in browser code.

## 10. Recovery prerequisites
Before any production use: configure automated encrypted database backups off the VPS, retain backups separately from the server, restrict access, and test restore into a clean environment. Write down who owns the recovery keys and escalation path. This kit does not configure offsite backups automatically.

## Current limitations
- Frontend remains a localStorage demo, not API-connected.
- No authentication, MFA, authorization or user provisioning yet.
- No Alembic migration system; current backend creates tables at startup.
- Order concurrency/idempotency needs database-level hardening and stress tests.
- Audit events are in the application database and are not yet externally tamper-evident.
- No market data adapter, instrument master, exchange calendar, historical backtest engine, notification worker, or broker order adapter.
- No live trading endpoint is implemented; keep it that way until all gates pass.
