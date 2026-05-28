# Deploy — `lucas-amc.appzoi.com.br`

Stack: Docker Compose com app FastAPI, Postgres 16 e Caddy 2 (TLS automático).

## Pré-requisitos

1. **VPS Linux** (Ubuntu 22.04+) com root ou sudo.
2. **Docker + Docker Compose v2** instalados.
3. **Portas 80 e 443** abertas no firewall.
4. **DNS A** de `lucas-amc.appzoi.com.br` → IP da VPS (verifique com `dig +short lucas-amc.appzoi.com.br`).

## 1. Clonar repo na VPS

```bash
git clone https://github.com/raul-behnke/zaf-amcveiculos-v4.git /opt/zoi
cd /opt/zoi/deploy
```

## 2. Criar `.env.prod`

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Preencha:
- `OPENAI_API_KEY` (gere nova no dashboard OpenAI — não reuse a de dev)
- `GHL_PIT_TOKEN` (PIT do GHL)
- `WEBHOOK_SECRET=$(openssl rand -hex 32)` — secret longo aleatório
- `POSTGRES_PASSWORD=$(openssl rand -hex 24)` — senha forte do DB

Os demais IDs (custom values, calendar, workflow) já vêm preenchidos com os valores reais.

## 3. Subir a stack

```bash
docker compose -f compose.prod.yml --env-file .env.prod up -d --build
```

Caddy demora ~60s pra obter TLS na 1ª execução. Acompanhe:

```bash
docker compose -f compose.prod.yml logs -f caddy
docker compose -f compose.prod.yml logs -f app
```

## 4. Validar

```bash
# Health endpoint (local)
docker compose -f compose.prod.yml exec app curl -s http://localhost:8000/health

# Health endpoint (público, via TLS)
curl -fsSL https://lucas-amc.appzoi.com.br/health
# esperado: {"status":"ok","db":true}

# Secret rejeitado
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST "https://lucas-amc.appzoi.com.br/webhook/inbound?secret=errado"
# esperado: 403
```

## 5. Atualizar config GHL

Substitua a URL dos workflows GHL para:

```
Saudação: https://lucas-amc.appzoi.com.br/sessions/{{contact.id}}/greet?secret=<WEBHOOK_SECRET>
Inbound:  https://lucas-amc.appzoi.com.br/webhook/inbound?secret=<WEBHOOK_SECRET>
Abandon:  https://lucas-amc.appzoi.com.br/sessions/{{contact.id}}/abandon?secret=<WEBHOOK_SECRET>
```

Apague workflows antigos apontando pra ngrok ou caminhos errados (`/webhooks/ghl/inbound`).

## Operação

| Tarefa | Comando |
|---|---|
| Logs app (follow) | `docker compose -f compose.prod.yml logs -f app` |
| Restart app | `docker compose -f compose.prod.yml restart app` |
| Update código | `git pull && docker compose -f compose.prod.yml up -d --build app` |
| Backup DB | `docker compose -f compose.prod.yml exec postgres pg_dump -U zoi zoi_agent > /var/backups/zoi-$(date +%F).sql` |
| Shell app | `docker compose -f compose.prod.yml exec app bash` |
| Métricas | `curl -s http://localhost:8000/metrics` (de dentro da VPS) |
| Parar tudo | `docker compose -f compose.prod.yml down` (mantém volumes) |

## Backup automático (sugestão)

```bash
# /etc/cron.daily/zoi-pgdump
#!/bin/sh
cd /opt/zoi/deploy
docker compose -f compose.prod.yml exec -T postgres \
  pg_dump -U zoi zoi_agent | gzip > /var/backups/zoi-$(date +%F).sql.gz
find /var/backups -name "zoi-*.sql.gz" -mtime +14 -delete
```

```bash
chmod +x /etc/cron.daily/zoi-pgdump
```

## Hardening pós-deploy

1. **Trocar senha root** (`passwd root`) e configurar **SSH key**, desabilitar login por senha em `/etc/ssh/sshd_config`.
2. **UFW**: liberar só portas 22, 80, 443.
3. **Proteger /metrics** — descomente a seção no `Caddyfile` e gere hash bcrypt com `docker run caddy caddy hash-password`.
4. **Fail2ban** pra proteger SSH.
5. **Rotate WEBHOOK_SECRET** trimestral.

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| 502 Bad Gateway | App não subiu | `docker compose logs app` — provavelmente env var faltando |
| Caddy não obtém TLS | DNS não propagou | `dig lucas-amc.appzoi.com.br` deve apontar pro IP |
| 403 em todos endpoints | Secret errado no GHL | Re-cole `WEBHOOK_SECRET` no workflow |
| `db: false` no /health | Postgres não respondeu | `docker compose logs postgres` |
