#!/usr/bin/env bash
# Actualiza lighttpd no servidor para suportar www (ACME + redirect HTTPS)
set -euo pipefail
CONF=/etc/lighttpd/lighttpd.conf
cp -a "$CONF" "${CONF}.bak-www-$(date +%Y%m%d%H%M%S)"
python3 <<'PY'
from pathlib import Path
conf = Path("/etc/lighttpd/lighttpd.conf")
text = conf.read_text()
old_http = '''$HTTP["host"] == "estacaboavista.com.br" {

    $HTTP["url"] =~ "^/.well-known/acme-challenge/" {

        server.document-root = "/var/www/estacaboavista-acme"

    }

    else {

        proxy.server = ( "" => ( ( "host" => "127.0.0.1", "port" => 5005 ) ) )

    }

}'''
new_http = '''$HTTP["host"] =~ "^(www\\.)?estacaboavista\\.com\\.br$" {

    $HTTP["url"] =~ "^/.well-known/acme-challenge/" {

        server.document-root = "/var/www/estacaboavista-acme"

    }

    else {

        proxy.server = ( "" => ( ( "host" => "127.0.0.1", "port" => 5005 ) ) )

    }

}'''
if old_http in text:
    text = text.replace(old_http, new_http, 1)
    print("HTTP: www ACME activo")
elif "www.estacaboavista.com.br" in text:
    print("HTTP: já tinha www")
else:
    print("HTTP: padrão não encontrado — verificar manualmente")
ssl_old = '''    # estacaboavista.com.br — SSL
    $HTTP["host"] == "estacaboavista.com.br" {

        ssl.pemfile = "/etc/letsencrypt/live/estacaboavista.com.br/fullchain.pem"

        ssl.privkey = "/etc/letsencrypt/live/estacaboavista.com.br/privkey.pem"

        setenv.add-request-header = ( "X-Forwarded-Proto" => "https" )

    }'''
ssl_www = '''

    # www → canónico
    $HTTP["host"] == "www.estacaboavista.com.br" {

        ssl.pemfile = "/etc/letsencrypt/live/estacaboavista.com.br/fullchain.pem"

        ssl.privkey = "/etc/letsencrypt/live/estacaboavista.com.br/privkey.pem"

        url.redirect-code = 301

        url.redirect = ( "^/(.*)" => "https://estacaboavista.com.br/$1" )

    }'''
if ssl_old in text and 'www.estacaboavista.com.br' not in text:
    text = text.replace(ssl_old, ssl_old + ssl_www, 1)
    print("SSL: redirect www adicionado")
conf.write_text(text)
PY
lighttpd -tt -f "$CONF"
systemctl reload lighttpd
echo OK
