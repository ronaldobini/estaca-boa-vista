# Estaca Boa Vista

Portal da Estaca Boa Vista — chamados, utilizadores e fluxo de indicações.

- **Produção:** https://estacaboavista.com.br
- **Login:** https://estacaboavista.com.br/entrar

## Stack

Flask + Gunicorn + MySQL (partilha tabelas `bini_*` com dados existentes).

## Deploy (servidor)

```bash
bash /root/repos/estaca-boa-vista/scripts/estaca-bv-update.sh
```

Serviço systemd: `estaca-boa-vista` (porta 5005).
