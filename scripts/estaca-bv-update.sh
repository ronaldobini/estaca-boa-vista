#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${ESTACA_BV_ROOT:-/root/repos/estaca-boa-vista}"
BRANCH="${ESTACA_BV_GIT_BRANCH:-main}"
cd "$APP_ROOT" || exit 1
echo "==> $(date -Is) estaca-bv-update: $APP_ROOT"
git fetch origin "$BRANCH"
git pull --ff-only origin "$BRANCH"
"$APP_ROOT/venv/bin/pip" install -q -r requirements.txt
systemctl restart estaca-boa-vista
systemctl is-active estaca-boa-vista
curl -sf "http://127.0.0.1:5005/health"
echo "OK"
