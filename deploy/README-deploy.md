# Deploy — `leonardo-castro.appzoi.com.br`

Stack: Docker Compose (app FastAPI + Postgres 16) atrás de **nginx host-level**
com TLS via Let's Encrypt (certbot).

## Pré-requisitos

1. **VPS Linux** com Docker + Compose v2, nginx e certbot já instalados.
2. **DNS A** de `leonardo-castro.appzoi.com.br` → IP da VPS.
3. **Portas 80 e 443** abertas no firewall (já em uso pelo nginx).
4. Porta interna `127.0.0.1:8000` livre (a app vai bindar nela).

## 1. Clonar repo na VPS

```bash
git clone https://github.com/raul-behnke/leonardo-castro.git /opt/leonardo-castro
cd /opt/leonardo-castro/deploy
```

## 2. Criar `.env.prod`

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Preencher pelo menos:
- `OPENAI_API_KEY`
- `GHL_PIT_TOKEN`
- `WEBHOOK_SECRET=$(openssl rand -hex 32)`
- `POSTGRES_PASSWORD=$(openssl rand -hex 24)`

Os IDs do GHL (custom values, calendar, workflow) já vêm preenchidos.

## 3. Subir Postgres + App

```bash
cd /opt/leonardo-castro/deploy
docker compose -f compose.prod.yml --env-file .env.prod up -d --build
```

Verificar que app sobe na porta local:

```bash
curl -s http://127.0.0.1:8000/health
# esperado: {"status":"ok","db":true}
```

## 4. Configurar nginx + TLS

```bash
# 4.1 Copia o vhost
cp nginx-vhost.conf /etc/nginx/sites-available/leonardo-castro.appzoi.com.br.conf
ln -sf /etc/nginx/sites-available/leonardo-castro.appzoi.com.br.conf \
       /etc/nginx/sites-enabled/leonardo-castro.appzoi.com.br

# 4.2 Obtém o certificado (vai instalar e recarregar nginx)
certbot --nginx -d leonardo-castro.appzoi.com.br --non-interactive --agree-tos -m admin@appzoi.com.br

# 4.3 Verifica config + reload
nginx -t && systemctl reload nginx
```

## 5. Validar fim-a-fim

```bash
# Public health
curl -fsSL https://leonardo-castro.appzoi.com.br/health
# esperado: {"status":"ok","db":true}

# Secret rejeitado
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "https://leonardo-castro.appzoi.com.br/webhook/inbound?secret=errado"
# esperado: 403
```

## 6. URLs pra GHL

```
Saudação: https://leonardo-castro.appzoi.com.br/sessions/{{contact.id}}/greet?secret=<WEBHOOK_SECRET>
Inbound:  https://leonardo-castro.appzoi.com.br/webhook/inbound?secret=<WEBHOOK_SECRET>
Abandon:  https://leonardo-castro.appzoi.com.br/sessions/{{contact.id}}/abandon?secret=<WEBHOOK_SECRET>
```

Apague workflows antigos apontando pra ngrok ou caminhos errados.

## Operação

| Tarefa | Comando |
|---|---|
| Logs app | `docker compose -f /opt/leonardo-castro/deploy/compose.prod.yml logs -f app` |
| Restart app | `docker compose -f /opt/leonardo-castro/deploy/compose.prod.yml restart app` |
| Update código | `cd /opt/leonardo-castro && git pull && cd deploy && docker compose -f compose.prod.yml up -d --build app` |
| Backup DB | `docker compose -f /opt/leonardo-castro/deploy/compose.prod.yml exec -T postgres pg_dump -U zoi zoi_agent | gzip > /var/backups/leonardo-castro-$(date +%F).sql.gz` |
| Shell app | `docker compose -f /opt/leonardo-castro/deploy/compose.prod.yml exec app bash` |
| nginx reload | `nginx -t && systemctl reload nginx` |
| Renovar TLS (automático) | `certbot renew --quiet` (certbot já agenda timer) |

## Backup automático

```bash
cat > /etc/cron.daily/leonardo-castro-pgdump <<'EOF'
#!/bin/sh
cd /opt/leonardo-castro/deploy
docker compose -f compose.prod.yml exec -T postgres \
  pg_dump -U zoi zoi_agent | gzip > /var/backups/leonardo-castro-$(date +%F).sql.gz
find /var/backups -name "leonardo-castro-*.sql.gz" -mtime +14 -delete
EOF
chmod +x /etc/cron.daily/leonardo-castro-pgdump
```

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| 502 Bad Gateway | App não respondeu na :8000 | `docker compose logs app` |
| Cert SSL falhou | DNS não propagou | `dig +short leonardo-castro.appzoi.com.br` |
| 403 em endpoints | Secret errado no GHL | Re-cole `WEBHOOK_SECRET` |
| `db: false` | Postgres não subiu | `docker compose logs postgres` |
| Conflito de porta | Outro processo na 8000 | `ss -tlnp \| grep 8000` |
