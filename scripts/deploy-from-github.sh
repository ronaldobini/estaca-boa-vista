#!/usr/bin/env bash
set -euo pipefail
APP=/root/repos/estaca-boa-vista
cd "$APP"
if [ ! -d .git ]; then
  git init
  git remote add origin https://github.com/ronaldobini/estaca-boa-vista.git 2>/dev/null || true
fi
git remote set-url origin https://github.com/ronaldobini/estaca-boa-vista.git
git fetch origin main
git reset --hard origin/main
if [ ! -d venv ]; then
  python3 -m venv venv
fi
./venv/bin/pip install -q --upgrade pip
./venv/bin/pip install -q -r requirements.txt
systemctl restart estaca-boa-vista
sleep 2
systemctl is-active estaca-boa-vista
curl -sf http://127.0.0.1:5005/health
echo
curl -sI https://estacaboavista.com.br/entrar | head -8
