# Docker — Ambiente Local

## Pré-requisitos

- Docker e Docker Compose v2+
- Arquivo `.env.docker` configurado (já incluído com defaults para desenvolvimento)

## Como Subir

### PostgreSQL + API

```bash
docker compose up
```

Isso inicia:
- **postgres** (porta 5432): PostgreSQL 16 com tabelas .NET (seed data) + py_* (Alembic migrations)
- **api** (porta 8000): FastAPI com hot-reload

### Com Admin UI

```bash
docker compose --profile admin up
```

Adiciona:
- **admin** (porta 8080): Interface NiceGUI para administração

## Verificação

```bash
# Health check
curl http://localhost:8000/health

# Trigger sync (modo local, sem chamadas externas)
curl -X POST "http://localhost:8000/sync/trigger" \
  -H "X-API-Key: dev-api-key-for-local"

# Ver appointments
curl "http://localhost:8000/sync/appointments?date=2026-03-10" \
  -H "X-API-Key: dev-api-key-for-local"

# Admin UI
open http://localhost:8080
```

## Migrations Manuais

```bash
# Executar migrations
docker compose exec api alembic upgrade head

# Ver estado atual
docker compose exec api alembic current

# Criar nova migration
docker compose exec api alembic revision -m "description"
```

## Seed Data

O arquivo `docker/init/02_seed_reference_data.sql` contém dados de exemplo. Para usar dados reais do banco de produção:

```bash
pg_dump --data-only --inserts \
  --table=sources --table=projects --table=regulation_systems \
  --table=project_regulation_systems --table=scrappers \
  --table=procedures --table=departments --table=department_execution_mapping \
  -h <host> -U <user> -d regulation > docker/init/02_seed_reference_data.sql
```

**Importante:** após alterar os init scripts, remova o volume para reinicializar:

```bash
docker compose down -v
docker compose up
```

## Variáveis de Ambiente

Ver `.env.docker` para configuração completa. Principais:

| Variável | Descrição | Default |
|----------|-----------|---------|
| `INTEGRATION_MODE` | `local` (sem APIs externas) ou `remote` | `local` |
| `WORKER_ENABLED` | Scheduler automático | `false` |
| `LOG_LEVEL` | Nível de log | `DEBUG` |
| `API_KEYS` | Chaves de autenticação da API | `dev-api-key-for-local` |
