#!/usr/bin/env bash
# Insere vhost estacaboavista.com.br no lighttpd.conf (idempotente, 2 fases)
set -euo pipefail

CONF=/etc/lighttpd/lighttpd.conf
ACME_ROOT=/var/www/estacaboavista-acme
DOMAIN=estacaboavista.com.br

phase_http() {
  if grep -q "estacaboavista.com.br — Estaca Boa Vista" "$CONF"; then
    echo "HTTP block já existe"
    return 0
  fi
  cp -a "$CONF" "${CONF}.bak-estaca-http-$(date +%Y%m%d%H%M%S)"
  python3 <<'PY'
from pathlib import Path
conf = Path("/etc/lighttpd/lighttpd.conf")
text = conf.read_text()
block = '''
# estacaboavista.com.br — Estaca Boa Vista (Gunicorn :5005)

$HTTP["host"] =~ "^(www\\.)?estacaboavista\\.com\\.br$" {

    $HTTP["url"] =~ "^/.well-known/acme-challenge/" {

        server.document-root = "/var/www/estacaboavista-acme"

    }

    else {

        proxy.server = ( "" => ( ( "host" => "127.0.0.1", "port" => 5005 ) ) )

    }

}

'''
needle = '# HTTP → HTTPS (mantém /.well-known para ACME). Em :443: proxy + SNI + X-Forwarded-Proto.'
if needle not in text:
    raise SystemExit("anchor não encontrado")
conf.write_text(text.replace(needle, block + "\n" + needle, 1))
print("HTTP block inserido")
PY
  lighttpd -tt -f "$CONF"
  systemctl reload lighttpd
}

phase_ssl() {
  if grep -q "estacaboavista.com.br — SSL" "$CONF"; then
    echo "SSL block já existe"
    return 0
  fi
  if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "Cert ainda não existe; a correr certbot..."
    certbot certonly --webroot --non-interactive --agree-tos --register-unsafely-without-email \
      -w "$ACME_ROOT" -d "$DOMAIN"
  fi
  cp -a "$CONF" "${CONF}.bak-estaca-ssl-$(date +%Y%m%d%H%M%S)"
  python3 <<'PY'
from pathlib import Path
conf = Path("/etc/lighttpd/lighttpd.conf")
text = conf.read_text()
block = '''
    # estacaboavista.com.br — SSL (apex)
    $HTTP["host"] == "estacaboavista.com.br" {

        ssl.pemfile = "/etc/letsencrypt/live/estacaboavista.com.br/fullchain.pem"

        ssl.privkey = "/etc/letsencrypt/live/estacaboavista.com.br/privkey.pem"

        setenv.add-request-header = ( "X-Forwarded-Proto" => "https" )

    }

    # www → canónico
    $HTTP["host"] == "www.estacaboavista.com.br" {

        ssl.pemfile = "/etc/letsencrypt/live/estacaboavista.com.br/fullchain.pem"

        ssl.privkey = "/etc/letsencrypt/live/estacaboavista.com.br/privkey.pem"

        url.redirect-code = 301

        url.redirect = ( "^/(.*)" => "https://estacaboavista.com.br/$1" )

    }

'''
needle = '    $HTTP["host"] == "tools.binisoft.com.br" {\n\n        ssl.pemfile = "/etc/letsencrypt/live/tools.binisoft.com.br/fullchain.pem"\n\n        ssl.privkey = "/etc/letsencrypt/live/tools.binisoft.com.br/privkey.pem"\n\n    }\n'
if needle not in text:
    raise SystemExit("anchor SSL não encontrado")
conf.write_text(text.replace(needle, needle + block, 1))
print("SSL block inserido")
PY
  lighttpd -tt -f "$CONF"
  systemctl reload lighttpd
}

case "${1:-all}" in
  http) phase_http ;;
  ssl) phase_ssl ;;
  all) phase_http; phase_ssl ;;
  *) echo "uso: $0 [http|ssl|all]"; exit 1 ;;
esac

echo "OK"
