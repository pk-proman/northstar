#!/usr/bin/env bash
set -euo pipefail
if [[ "$(. /etc/os-release && echo "$ID:$VERSION_ID")" != "ubuntu:24.04" ]]; then
  echo "This script is intended for Ubuntu 24.04 LTS only." >&2
  exit 1
fi
sudo apt-get update
sudo apt-get install -y ca-certificates curl docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo docker --version
sudo docker compose version
cat <<'MSG'
Docker is installed. For safer operations, continue using sudo docker rather than adding your user to the docker group (membership grants root-equivalent control).
Next: follow docs/HOSTINGER_SETUP.md.
MSG
