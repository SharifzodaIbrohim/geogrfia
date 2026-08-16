#!/usr/bin/env bash
# Deploy on Ubuntu: git pull + restart systemd service.
# Usage:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
#   SERVICE_NAME=geografia APP_DIR=/opt/geogrfia ./scripts/deploy.sh

set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SERVICE_NAME="${SERVICE_NAME:-geografia}"
BRANCH="${BRANCH:-main}"

echo "[deploy] dir=$APP_DIR branch=$BRANCH service=$SERVICE_NAME"

cd "$APP_DIR"

if [[ ! -d .git ]]; then
  echo "[deploy] ERROR: not a git repo: $APP_DIR" >&2
  exit 1
fi

echo "[deploy] git fetch + checkout $BRANCH"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [[ -f requirements.txt ]]; then
  if [[ -d .venv ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install -q -r requirements.txt
  elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
    pip install -q -r requirements.txt
  else
    echo "[deploy] skip pip (no .venv); activate venv if needed"
  fi
fi

if systemctl list-unit-files "${SERVICE_NAME}.service" 2>/dev/null | grep -q "${SERVICE_NAME}.service"; then
  echo "[deploy] systemctl restart $SERVICE_NAME"
  sudo systemctl restart "$SERVICE_NAME"
  sudo systemctl --no-pager --full status "$SERVICE_NAME" || true
else
  echo "[deploy] no systemd unit ${SERVICE_NAME}.service — restart gunicorn manually"
fi

echo "[deploy] done"
