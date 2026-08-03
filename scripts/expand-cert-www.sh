#!/usr/bin/env bash
# Expande certificado Let's Encrypt para incluir www (correr após CNAME www activo).
set -euo pipefail
DOMAIN=estacaboavista.com.br
ACME_ROOT=/var/www/estacaboavista-acme

echo "==> Verificar DNS www"
if ! dig +short www."$DOMAIN" A | grep -q .; then
  echo "ERRO: www.$DOMAIN ainda sem registo A/CNAME. Adiciona o CNAME no painel do domínio e espera propagação."
  exit 1
fi

certbot certonly --webroot --non-interactive --agree-tos --register-unsafely-without-email \
  --expand -w "$ACME_ROOT" -d "$DOMAIN" -d "www.$DOMAIN"

lighttpd -tt -f /etc/lighttpd/lighttpd.conf
systemctl reload lighttpd
echo "OK — cert inclui www.$DOMAIN"
