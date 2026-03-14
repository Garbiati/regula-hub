# RegulaHub

Plataforma de integração com sistemas de regulação brasileiros.

Expõe funcionalidades de sistemas como SisReg III através de endpoints REST, usando **requisições HTTP diretas** (sem Selenium, sem Playwright, sem automação de browser).

---

## Sobre o Projeto

### O Problema

A regulação do SUS opera através de múltiplos sistemas (SisReg III, e-SUS, SIGA, CARE, SER), cada um com diversas contas por unidade de saúde. Na prática, um operador precisa:

1. Fazer login manualmente em **11 contas diferentes**
2. Navegar menus complexos para cada conta
3. Copiar dados para planilhas Excel
4. Repetir para cada data de referência

Processo manual que consome horas por dia, propenso a erros e não escalável.

### A Solução

O RegulaHub funciona como uma **camada de integração** que:

- **Agrega múltiplas contas** em uma visão unificada via Admin UI
- **Automatiza a coleta** de dados via HTTP direto
- **Persiste credenciais** criptografadas no banco de dados
- **Suporta múltiplos sistemas** de regulação

### Sistemas Suportados

| Sistema | Abrangência | Status |
|---------|-------------|--------|
| **SISREG III** | Nacional (foco: AM) | Operacional |
| **e-SUS Regulação** | Nacional | Planejado |
| **SIGA Saúde** | São Paulo (SP) | Planejado |
| **CARE Paraná** | Paraná (PR) | Planejado |
| **SER (RJ)** | Rio de Janeiro (RJ) | Planejado |

> **Escopo atual:** Estado do **Amazonas (AM)**, sistema **SISREG III**.

---

## Stack Tecnológica

### Backend

| Componente | Tecnologia |
|------------|------------|
| Linguagem | Python 3.12 |
| Framework | FastAPI |
| HTTP Client | HTTPX (async) |
| Validação | Pydantic v2 + Settings |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Migrações | Alembic |
| Logging | structlog (JSON/console) |
| Rate Limiting | slowapi |
| Criptografia | cryptography (Fernet) |
| Gerenciador | Poetry |
| Testes | Pytest + respx + pytest-cov |
| Lint/SAST | Ruff + Bandit + Gitleaks |

### Admin UI

| Componente | Tecnologia |
|------------|------------|
| Framework | Next.js 16 |
| UI | React 19 + TypeScript |
| Estilização | Tailwind CSS v4 + shadcn/ui |
| Data Fetching | TanStack Query v5 |
| Tabelas | TanStack Table v8 |
| Estado | Zustand v5 |
| i18n | next-intl (pt-BR, en-US, es-AR) |
| Testes | Vitest + Playwright + MSW |

### Infraestrutura

| Componente | Tecnologia |
|------------|------------|
| Banco | PostgreSQL 16 |
| Containers | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Hooks | pre-commit (Ruff, Bandit, Gitleaks) |

---

## Arquitetura

```
Operador → Admin UI (Next.js :3000) → API (FastAPI :8000) → Sistema de Regulação (HTTP)
                                              ↕
                                          PostgreSQL
```

### Estrutura de Diretórios

```
src/regulahub/
  api/               FastAPI routes, dependencies, schemas
    controllers/
      admin/          Admin API (credentials, systems, users)
      regulation/     Endpoints compatíveis com ptm-regulation-service
      raw/            Passthrough para dados brutos do SisReg
  client/             HTTP session, navegação, parser HTML
  config.py           Pydantic Settings (lazy-loaded via @lru_cache)
  db/                 SQLAlchemy models, engine, repositories
    repositories/     Data access layer
  main.py             FastAPI app entry point
  models/             Pydantic domain models
  scripts/            Seed de credenciais (seed_credentials, export_credentials)
  selectors/          CSS selectors centralizados para parsing HTML
  services/           Orquestração de negócio
  utils/              Crypto (SHA-256), extração de telefone, masking de PII

admin/src/
  app/                Next.js App Router pages
  components/         React components (layout, shared, feature-specific)
  hooks/              TanStack Query hooks
  lib/                API client, constantes, utils
  providers/          Query, Theme, I18n providers
  stores/             Zustand stores
  types/              TypeScript interfaces
  i18n/               Configuração next-intl
```

---

## Início Rápido

### Pré-requisitos

- Docker + Docker Compose
- Python 3.12+ e Poetry (para desenvolvimento backend)
- Node.js 22+ e pnpm 9+ (para desenvolvimento frontend)

### Docker Compose (recomendado)

```bash
# Copiar e configurar variáveis de ambiente
cp .env.example .env
# Editar .env — gerar CREDENTIAL_ENCRYPTION_KEY e definir API_KEYS

# Subir todos os serviços
docker compose up -d

# API:   http://localhost:8000
# Admin: http://localhost:3000
# Health: http://localhost:8000/health
```

O Docker Compose executa automaticamente:
1. PostgreSQL 16 com scripts de inicialização
2. Migrações Alembic (`alembic upgrade head`)
3. Seed de credenciais
4. API com hot reload
5. Admin UI com hot reload

### Setup Manual

```bash
# Backend
poetry install
poetry run pre-commit install
poetry run alembic upgrade head
poetry run uvicorn regulahub.main:app --reload

# Frontend (em outro terminal)
pnpm --prefix admin install
pnpm --prefix admin dev
```

---

## Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

### Aplicação

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `LOG_LEVEL` | Não | `INFO` | Nível de log (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | Não | `console` | Formato de log (`console` ou `json`) |
| `CORS_ORIGINS` | Não | `*` | Origens CORS permitidas (separadas por vírgula) |

### Autenticação

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `API_KEYS` | **Sim** | — | API keys separadas por vírgula |

### Banco de Dados

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `DB_HOST` | Não | `localhost` | Host do PostgreSQL |
| `DB_PORT` | Não | `5432` | Porta do PostgreSQL |
| `DB_NAME` | Não | `regulahub` | Nome do banco |
| `DB_USER` | **Sim** | — | Usuário do banco |
| `DB_PASSWORD` | **Sim** | — | Senha do banco |
| `DB_POOL_SIZE` | Não | `10` | Tamanho do pool de conexões |
| `DB_MAX_OVERFLOW` | Não | `20` | Conexões extras além do pool |
| `DB_POOL_TIMEOUT` | Não | `10` | Timeout do pool (segundos) |

### Segurança

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `CREDENTIAL_ENCRYPTION_KEY` | **Sim** | — | Chave Fernet (44 chars, base64) |

Gerar com: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### Admin UI

| Variável | Obrigatória | Default | Descrição |
|----------|-------------|---------|-----------|
| `ADMIN_API_URL` | Não | `http://localhost:8000` | URL base da API para o admin |
| `ADMIN_STORAGE_SECRET` | Não | (dev default) | Secret para persistência de sessão |

---

## Desenvolvimento

### Comandos do Backend

| Comando | Descrição |
|---------|-----------|
| `poetry install` | Instalar dependências |
| `poetry run pytest tests/ -v` | Rodar todos os testes |
| `poetry run pytest tests/unit/ -v` | Apenas testes unitários |
| `poetry run pytest tests/ -v --cov` | Testes com coverage |
| `poetry run ruff check src/ tests/` | Lint |
| `poetry run ruff format src/ tests/` | Formatação |
| `poetry run bandit -c pyproject.toml -r src/` | SAST scan |
| `poetry run pre-commit run --all-files` | Rodar todos os hooks |
| `poetry run uvicorn regulahub.main:app --reload` | Rodar API localmente |

### Comandos do Frontend

| Comando | Descrição |
|---------|-----------|
| `pnpm --prefix admin install` | Instalar dependências |
| `pnpm --prefix admin dev` | Dev server (port 3000) |
| `pnpm --prefix admin build` | Build de produção |
| `pnpm --prefix admin lint` | Lint (ESLint) |
| `pnpm --prefix admin format` | Formatação (Prettier) |
| `pnpm --prefix admin test` | Testes unitários (Vitest) |
| `pnpm --prefix admin test:watch` | Testes em watch mode |
| `pnpm --prefix admin test:coverage` | Testes com coverage (v8) |
| `pnpm --prefix admin test:e2e` | Testes E2E (Playwright) |

### Docker

| Comando | Descrição |
|---------|-----------|
| `docker compose up -d` | Subir todos os serviços |
| `docker compose down` | Parar todos os serviços |
| `docker compose logs -f api` | Logs da API |
| `docker compose exec api alembic upgrade head` | Rodar migrações |
| `docker compose exec api alembic revision --autogenerate -m "desc"` | Criar migração |

### Pre-commit Hooks

Instalados automaticamente em commits. Inclui:

- **Ruff** — lint (`--fix`) + formatação
- **Bandit** — SAST scan em `src/`
- **Gitleaks** — detecção de secrets
- **pre-commit-hooks** — detecção de chaves privadas, arquivos grandes (>500KB), conflitos de merge, trailing whitespace

```bash
# Instalar hooks
poetry run pre-commit install

# Rodar manualmente
poetry run pre-commit run --all-files
```

---

## Testes

### Backend

- **Framework:** Pytest + pytest-asyncio + respx (mock HTTP)
- **DB em testes:** SQLite (aiosqlite) — sem PostgreSQL necessário
- **Coverage mínimo:** 70% (configurado em `pyproject.toml`)
- **Fixtures HTML:** `tests/fixtures/` contém snapshots reais do SisReg

```bash
poetry run pytest tests/ -v --cov --cov-report=term-missing
```

### Frontend

- **Unitários/Integração:** Vitest + Testing Library + MSW (Mock Service Worker)
- **E2E:** Playwright (chromium)
- **Estrutura:** `admin/tests/unit/`, `admin/tests/integration/`, `admin/tests/e2e/`

```bash
pnpm --prefix admin test              # unitários
pnpm --prefix admin test:coverage     # com coverage
pnpm --prefix admin test:e2e          # E2E
```

### Postman Collection

Collection com 3 grupos de requests, test scripts automatizados e 2 ambientes (Local/Staging).

```
postman/
  regula-hub.postman_collection.json
  environments/
    local.postman_environment.json
    staging.postman_environment.json
```

**Como usar:** File → Import no Postman → selecionar os 3 JSONs → escolher ambiente.

---

## CI/CD

### GitHub Actions

Pipeline em `.github/workflows/ci.yml`, executado em PRs para `dev`, `staging`, `master` e pushes em `dev`.

**Job Backend:**
1. Lint (Ruff)
2. Format check (Ruff)
3. SAST (Bandit)
4. Testes com coverage (PostgreSQL 16 como service)

**Job Frontend:**
1. Lint (ESLint)
2. Type check + Build (Next.js)
3. Testes (Vitest)

---

## Segurança e LGPD

| Proteção | Implementação |
|----------|---------------|
| Criptografia de credenciais | Fernet (AES-128-CBC + HMAC) |
| PII masking | Logs nunca contêm CPF, CNS, telefone ou nome |
| Rate limiting | slowapi em todos os endpoints |
| Tracing | X-Request-ID em todas as requests |
| CORS | Origens configuráveis (restritivo em produção) |
| Autenticação | API key via header `X-API-Key` |
| SAST | Pipeline Bandit + Ruff (regras S) + Gitleaks |
| Somente leitura | Nenhuma operação de escrita nos sistemas de regulação |

Relatório completo de auditoria em [docs/audit/QA_REPORT.md](docs/audit/QA_REPORT.md).

---

## Documentação

### Leitura Obrigatória

Antes de qualquer modificação, leia estes documentos na ordem:

| # | Documento | Propósito | Quando Ler |
|---|-----------|-----------|------------|
| 1 | [`CONSTITUTION.md`](docs/specs/CONSTITUTION.md) | Princípios invioláveis do projeto | Sempre (primeira leitura) |
| 2 | [`BUSINESS_RULES.md`](docs/specs/BUSINESS_RULES.md) | Regras de negócio do SisReg e domínio | Antes de tocar no domínio |
| 3 | [`TECH_SPEC.md`](docs/specs/TECH_SPEC.md) | Arquitetura técnica e decisões | Antes de decisões técnicas |
| 4 | [`BACKEND_GUARDRAILS.md`](docs/specs/BACKEND_GUARDRAILS.md) | Normas e padrões do backend | Antes de qualquer mudança backend |
| 5 | [`ADMIN_FRONTEND_ARCHITECTURE.md`](docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md) | Normas e padrões do frontend | Antes de qualquer mudança frontend |

### Documentação Completa

| Documento | Propósito |
|-----------|-----------|
| [`SOBRE_O_PROJETO.md`](docs/SOBRE_O_PROJETO.md) | Visão do produto, personas, escopo |
| [`QA_REPORT.md`](docs/audit/QA_REPORT.md) | Relatório de auditoria de segurança e qualidade |
| [`PROMOTION_FLOW.md`](docs/workflows/PROMOTION_FLOW.md) | Pipeline de promoção dev → staging → master |
| [`ARCHITECTURE_DIAGRAM.md`](docs/architecture/ARCHITECTURE_DIAGRAM.md) | Diagrama de arquitetura |
| [`ENGINEERING_GUIDELINES.md`](docs/code-quality/ENGINEERING_GUIDELINES.md) | Diretrizes de engenharia |
| [`SECURITY_REPORT.md`](docs/code-quality/SECURITY_REPORT.md) | Relatório de segurança |
| [`docs/specs/features/*.md`](docs/specs/features/) | Specs individuais de features |

---

## Git Workflow

### Branching Strategy

```
feature/fix branch → dev → staging → master
```

- **Nunca** commitar diretamente em `dev`, `staging` ou `master`
- Feature branches sempre saem de `master`
- Prefixos: `feat/`, `fix/`, `chore/`, `refactor/`, `docs/`, `test/`

### Commit Conventions

[Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add appointment filtering by procedure code
fix: correct session timeout handling
chore: update pre-commit hooks
refactor: extract phone parsing to utility
```

### PR Flow

1. Criar branch de `master` → PR para `dev`
2. Review + merge → PR de `dev` para `staging`
3. Validação → PR de `staging` para `master`

Template de PR em `.github/PULL_REQUEST_TEMPLATE.md`. Detalhes do fluxo de promoção em [`PROMOTION_FLOW.md`](docs/workflows/PROMOTION_FLOW.md).

---

## SisReg III

O [SisReg](https://wiki.saude.gov.br/SISREG/index.php/P%C3%A1gina_principal) (Sistema Nacional de Regulação) é um sistema web do **DATASUS/Ministério da Saúde** que gerencia o Complexo Regulador do SUS. Este serviço integra com o **SisReg III** (versão atual, desde 2006), focado em procedimentos ambulatoriais e internações hospitalares.

### Abordagem: HTTP Direto

O SisReg não possui API pública. Este serviço faz **requisições HTTP diretas** (sem browser automation) porque o SisReg é uma aplicação CGI clássica com formulários HTML padrão:

- **Autenticação**: POST para `/` com senha em SHA-256
- **Navegação**: POSTs de formulário e links — cada página é HTML completo
- **Dados**: Embutidos em tabelas HTML, extraídos via parsing
- **Sessão**: Cookies no servidor (`SESSION`, `ID`)

### Perfis Utilizados

| Perfil | Escopo | Uso |
|--------|--------|-----|
| **Videofonista** | Estadual (todos os municípios) | Listagem de todos os agendamentos |
| **Solicitante/Executante** | Unidade de saúde | Detalhes de agendamentos da unidade |

Para detalhes completos sobre os 9 perfis do SisReg, regras de negócio e fluxo de extração, consulte [`BUSINESS_RULES.md`](docs/specs/BUSINESS_RULES.md).

---

## Referências

- [Wiki SisReg — Ministério da Saúde](https://wiki.saude.gov.br/SISREG/index.php/P%C3%A1gina_principal)
- [CONASS — O SisReg](https://www.conass.org.br/guiainformacao/o-sisreg/)
- [SisReg III — Portal Gov.br](https://www.gov.br/saude/pt-br/acesso-a-informacao/gestao-do-sus/articulacao-interfederativa/cit/pautas-de-reunioes-e-resumos/2017/janeiro/3-b-sisreg-cit.pdf)
