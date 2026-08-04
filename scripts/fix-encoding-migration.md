#!/usr/bin/env bash
# Repõe textos UTF-8 em bini_estaca_calling_events.detail após migração com charset errado.
# Gerar SQL no Vultr (fonte correcta): bash scripts/gen-fix-events-sql.sh
# Aplicar no Hetzner: mysql estaca_boa_vista < fix-estaca-events-utf8.sql
set -euo pipefail
echo "Ver docs: usar gen-fix-events-sql.sh no servidor Vultr com binitools, depois mysql no Hetzner."
