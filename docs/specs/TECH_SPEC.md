# Especificação Técnica

Decisões técnicas e restrições arquiteturais deste serviço.

## Escopo Atual

O serviço atualmente fornece:

- **Admin API** — CRUD de credenciais, sistemas de regulação e usuários
- **Admin UI** — Dashboard Next.js para gestão de credenciais e configuração de sistemas
- **Infraestrutura** — Banco de dados, migrações, criptografia de credenciais

> **Nota:** O pipeline de scraping SisReg (worker, client HTTP, parser HTML, integration adapters) foi removido. A comunicação futura com o SisReg III usará a abordagem de **HTTP direto** (sem browser automation), conforme detalhado em specs de features específicas.

## Arquitetura de Camadas

```text
[API Layer]         -> Endpoints REST (Admin CRUD), DTOs de entrada/saída
[Service Layer]     -> Orquestração de negócio (credenciais, sistemas, usuários)
[DB Layer]          -> SQLAlchemy models, repositories, engine
```

### Responsabilidades

| Camada          | Responsabilidade                                         | NÃO faz                              |
|-----------------|----------------------------------------------------------|---------------------------------------|
| API Layer       | Validar input, serializar output, HTTP status codes      | Lógica de negócio                     |
| Service Layer   | Orquestrar fluxo, aplicar regras de negócio              | Acesso direto ao banco                |
| DB Layer        | Mapeamento ORM, queries, transações                      | Regras de negócio, validação de input |

## Tratamento de Erros

| Cenário                        | Ação                                                    |
|--------------------------------|---------------------------------------------------------|
| Credencial inválida/não encontrada | Retornar erro 4xx com mensagem genérica               |
| Falha de decriptografia        | Logar erro internamente, retornar 503                    |
| Banco de dados indisponível    | Retornar erro 503, incluir detalhes no log              |
| Input inválido                 | Retornar erro 422 com detalhes de validação             |

## Padrões de Banco de Dados

- Pool configuration: `pool_size`, `max_overflow`, `pool_timeout` configuráveis via env vars
  - Defaults de produção: pool_size=10, max_overflow=20, pool_timeout=10
- Toda mutação de dados DEVE usar `async with db.begin()` para atomicidade
- Repository NUNCA faz commit — apenas flush. Quem controla transação é o Service
- N+1 prevention: NUNCA fazer query dentro de loop — usar IN clause ou JOIN
- Paginação obrigatória: todo endpoint de listagem DEVE ter `skip`/`limit` com limites

## Padrões de API

- Rate limiting via slowapi: todo endpoint DEVE ter `@limiter.limit()` decorator
- Error response padronizado: `{"detail": "...", "error_code": "..."}` via `ErrorResponse` schema
- Input validation: todo campo string em schema de input DEVE ter `min_length`/`max_length`
- Request/Response logging: middleware obrigatório com method, path, status, latency
- CORS: headers DEVEM ser lista explícita — NUNCA wildcard

## Observabilidade

- X-Request-ID: gerado pelo middleware se ausente, propagado via structlog contextvars
- Structured logging: structlog obrigatório, JSON em produção, console em dev
- PII masking: todo dado de usuário em logs DEVE usar `mask_username()` de `utils/masking.py`
- Health check: DEVE validar todas as dependências críticas (DB, chave Fernet, etc.)
- Falhas de autenticação: DEVEM ser logadas com IP e timestamp

## Testes

### Estratégia de Testes

```text
Unit Tests       -> Serviços, configuração, validação, regras de negócio
Integration Tests -> Fluxo completo com banco SQLite (aiosqlite)
E2E Tests        -> Admin UI via Playwright (chromium)
```

## Estrutura de Diretórios

```text
regula-hub/
  readme.md
  CLAUDE.md
  .pre-commit-config.yaml   # Pipeline SAST local
  Dockerfile                 # Build de produção (multi-stage)
  Dockerfile.dev             # Build de desenvolvimento
  docker-compose.yml         # Dev local com hot reload
  docs/
    specs/
      CONSTITUTION.md        # Princípios invioláveis
      BUSINESS_RULES.md      # Regras de negócio
      TECH_SPEC.md           # Este arquivo
      features/              # Specs de funcionalidades individuais
    audit/
      QA_REPORT.md           # Relatório de auditoria QA/segurança
  postman/                   # Collection e environments Postman
  admin/                     # Next.js 16 Admin UI (React 19, Tailwind v4, shadcn/ui)
  src/regulahub/
    api/                     # FastAPI routes, deps, schemas
      controllers/
        admin/               # Admin API endpoints (credentials, systems, users)
    db/                      # SQLAlchemy models, engine, session
      repositories/          # Data access layer (Repository Pattern)
    services/                # Orquestração de negócio (credential_service)
    scripts/                 # Credential management (seed, export)
    utils/                   # Crypto, phone, PII masking
    config.py                # Pydantic Settings (.env)
    logging_config.py        # structlog configuration
    main.py                  # FastAPI app entry point
  alembic/
    versions/                # Migrações de banco de dados
  docker/
    init/                    # Scripts de inicialização PostgreSQL (seed data)
  tests/
    fixtures/                # Fixtures de teste
    unit/                    # Testes unitários
    integration/             # Testes de integração
```

## Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| Linguagem | Python 3.12 | Async nativo, ecossistema maduro |
| Framework | FastAPI | REST API async, validação automática via Pydantic |
| HTTP Client | HTTPX | Async HTTP client |
| Validação | Pydantic v2 + Settings | Type-safe, validação de env vars via `.env` |
| ORM | SQLAlchemy 2.0 (async) | Mapeamento ORM async, Repository Pattern |
| DB Driver | asyncpg | Driver PostgreSQL async nativo, alta performance |
| Migrações | Alembic | Migrações versionadas, auto-generate a partir dos models |
| Logging | structlog | Logging estruturado, JSON em produção, contextvars |
| Rate Limiting | slowapi | Rate limiting por endpoint, baseado em limits |
| Criptografia | cryptography | Fernet encryption para credenciais armazenadas |
| Gerenciador | Poetry | Lock file, grupos de deps (dev/prod) |
| Testes | Pytest + respx | Async tests, HTTP mocking sem servidor real |
| Lint/SAST | Ruff + Bandit | Lint rápido + SAST Python (OWASP) |
