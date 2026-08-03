#!/usr/bin/env bash
# Setup inicial no servidor: estacaboavista.com.br (executar como root no BiniSoft1)
set -euo pipefail

APP_ROOT=/root/repos/estaca-boa-vista
APP_PORT=5005
DOMAIN=estacaboavista.com.br
ACME_ROOT=/var/www/estacaboavista-acme
UPLOAD_ROOT=/var/lib/estaca-boa-vista/uploads
echo "==> Criar estrutura de pastas"
mkdir -p "$APP_ROOT"/app/static/css "$APP_ROOT"/scripts "$APP_ROOT"/deploy "$APP_ROOT"/.deploy-state
mkdir -p "$ACME_ROOT" "$UPLOAD_ROOT"
chown -R www-data:www-data "$ACME_ROOT"

cat > "$APP_ROOT/requirements.txt" <<'REQ'
Flask>=3.0.0
gunicorn>=22.0.0
python-dotenv>=1.0.0
REQ

cat > "$APP_ROOT/run.py" <<'PY'
"""Estaca Boa Vista — app standalone (placeholder até deploy do código real)."""
from flask import Flask
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")


@app.route("/health")
def health():
    return {"status": "ok", "app": "estaca-boa-vista"}, 200


@app.route("/")
def index():
    return (
        "<!DOCTYPE html><html lang=\"pt-BR\"><head>"
        "<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Estaca Boa Vista</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;color:#1e293b}"
        "h1{color:#1d4ed8}</style></head><body>"
        "<h1>Estaca Boa Vista</h1>"
        "<p>Portal em preparação. Em breve estará disponível em <strong>estacaboavista.com.br</strong>.</p>"
        "</body></html>",
        200,
    )
PY

cat > "$APP_ROOT/app/__init__.py" <<'PY'
# Estaca Boa Vista package
PY

cat > "$APP_ROOT/scripts/estaca-bv-update.sh" <<'UPD'
#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${ESTACA_BV_ROOT:-/root/repos/estaca-boa-vista}"
BRANCH="${ESTACA_BV_GIT_BRANCH:-main}"
cd "$APP_ROOT" || exit 1
echo "==> $(date -Is) estaca-bv-update: $APP_ROOT"
if [ -d .git ]; then
  git fetch origin "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi
if [ -f requirements.txt ]; then
  "$APP_ROOT/venv/bin/pip" install -q -r requirements.txt
fi
systemctl restart estaca-boa-vista
systemctl is-active estaca-boa-vista
UPD
chmod +x "$APP_ROOT/scripts/estaca-bv-update.sh"

if [ ! -d "$APP_ROOT/venv" ]; then
  python3 -m venv "$APP_ROOT/venv"
fi
"$APP_ROOT/venv/bin/pip" install -q --upgrade pip
"$APP_ROOT/venv/bin/pip" install -q -r "$APP_ROOT/requirements.txt"

if [ ! -f /etc/default/estaca-boa-vista ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > /etc/default/estaca-boa-vista <<EOF
SECRET_KEY=$SECRET
DATABASE_URL=mysql+pymysql://binitools:tcJCldstools26@127.0.0.1:3306/binitools?charset=utf8mb4
ESTACA_BV_UPLOAD_ROOT=$UPLOAD_ROOT
SESSION_COOKIE_SECURE=1
PREFERRED_URL_SCHEME=https
EOF
  chmod 600 /etc/default/estaca-boa-vista
fi

cat > /etc/systemd/system/estaca-boa-vista.service <<EOF
[Unit]
Description=Estaca Boa Vista (Gunicorn)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$APP_ROOT
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-/etc/default/estaca-boa-vista
ExecStart=$APP_ROOT/venv/bin/gunicorn -w 1 -b 127.0.0.1:$APP_PORT --timeout 120 run:app
Restart=on-failure
RestartSec=4

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable estaca-boa-vista
systemctl restart estaca-boa-vista
echo "==> Gunicorn :$APP_PORT"
systemctl is-active estaca-boa-vista
sleep 1
curl -sf "http://127.0.0.1:$APP_PORT/health" || { sleep 2; curl -sf "http://127.0.0.1:$APP_PORT/health"; }

echo "==> lighttpd + SSL (patch-lighttpd-estaca.sh)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SCRIPT_DIR/patch-lighttpd-estaca.sh" ]; then
  bash "$SCRIPT_DIR/patch-lighttpd-estaca.sh" all
elif [ -x /root/patch-lighttpd-estaca.sh ]; then
  bash /root/patch-lighttpd-estaca.sh all
else
  echo "AVISO: patch-lighttpd-estaca.sh não encontrado — correr manualmente no servidor."
fi

echo "==> Verificação final"
curl -sf "http://127.0.0.1:$APP_PORT/health"
curl -sI "https://$DOMAIN/" | head -8
echo "OK — $DOMAIN pronto em $APP_ROOT (porta $APP_PORT)"
