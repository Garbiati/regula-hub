# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Spec-First Development

This project follows **Spec-Driven Development**. You MUST read the relevant spec before writing any code.

### Mandatory Reading Order

Before ANY modification, read these files in order:

1. [docs/specs/CONSTITUTION.md](docs/specs/CONSTITUTION.md) - Inviolable principles
2. [docs/specs/BUSINESS_RULES.md](docs/specs/BUSINESS_RULES.md) - Domain rules and constraints
3. [docs/specs/TECH_SPEC.md](docs/specs/TECH_SPEC.md) - Technical architecture
4. **[docs/specs/BACKEND_GUARDRAILS.md](docs/specs/BACKEND_GUARDRAILS.md)** - Backend norms (**read before any backend change**)
5. [docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md](docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md) - Frontend norms (**read before any admin UI change**)
6. The specific feature spec in `docs/specs/features/` (if applicable)

### Workflow

NEVER write code without a spec. NEVER change behavior without updating the spec first.

1. Read the spec for the feature/fix
2. If no spec exists, create one in `docs/specs/features/` and get approval before coding
3. Implement according to the spec
4. Write tests that validate the spec's acceptance criteria
5. Verify existing tests still pass

## Service Overview

**regula-hub** is a WebAPI for managing regulation system credentials, user profiles, and multi-system integration configuration.

## Stack

Python 3.12, FastAPI, HTTPX (async HTTP client), Pydantic v2/Settings, Poetry, Pytest + respx, Ruff, SQLAlchemy 2.0 (async) + asyncpg, Alembic, structlog. Admin UI: Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query/Table, Zustand, next-intl.

## Commands

- `poetry install` — install dependencies
- `poetry run pytest tests/ -v` — run all tests
- `poetry run pytest tests/unit/ -v` — run unit tests only
- `poetry run pytest tests/unit/test_parser.py -v` — run a single test file
- `poetry run pytest tests/unit/test_parser.py::test_function_name -v` — run a single test
- `poetry run ruff check src/ tests/` — lint
- `poetry run ruff format src/ tests/` — format
- `poetry run bandit -c pyproject.toml -r src/` — SAST scan
- `poetry run pre-commit run --all-files` — run all pre-commit hooks
- `poetry run uvicorn regulahub.main:app --reload` — run API locally
- `docker compose up -d` — run full stack (PostgreSQL + API + Admin UI)
- `pnpm --prefix admin dev` — run admin UI locally (dev mode)
- `pnpm --prefix admin build` — build admin UI for production
- `pnpm --prefix admin lint` — lint admin frontend code
- `pnpm --prefix admin test` — run admin frontend tests (Vitest)
- `pnpm --prefix admin test:watch` — run admin tests in watch mode
- `pnpm --prefix admin test:coverage` — run admin tests with v8 coverage
- `pnpm --prefix admin test:e2e` — run admin Playwright E2E tests
- `pnpm --prefix admin format` — format admin frontend code (Prettier)
- `poetry run pytest --cov=regulahub tests/ -v` — run tests with coverage (fail_under=70)
- `docker compose exec api alembic upgrade head` — run migrations manually
- `docker compose exec api alembic revision -m "description"` — create new migration

**Note:** If `poetry run` fails with virtualenv issues, use the venv binary directly: `/home/alessandro/.cache/pypoetry/virtualenvs/ptm-regula-hub-R68SipPr-py3.12/bin/python -m pytest ...`

### Pre-commit Hooks

Commits run these hooks automatically (all must pass):

- **ruff** — lint (`--fix`) + format
- **bandit** — SAST scan on `src/`
- **gitleaks** — secrets detection
- **pre-commit-hooks** — detect private keys, large files (>500KB), merge conflicts, trailing whitespace, EOF fixer

### Ruff Configuration

- `line-length = 120`, `target-version = "py312"`
- Ignored rules: `B008` (function call in default args — required for FastAPI `Depends()`), `A005` (module shadowing), `S101` (assert in tests)

## Architecture

```text
src/regulahub/
  api/
    deps.py                  Auth dependency (X-API-Key, timing-safe HMAC)
    routes.py                Health/status endpoints
    rate_limit.py            slowapi.Limiter instance
    controllers/
      admin/                 Admin CRUD (credentials, systems, users, sisreg)
      compat/                Absens-compatible migration endpoints (separate auth)
  services/                  Business logic orchestration
    credential_service.py    Credential resolution + encryption
    compat_service.py        Absens DTO mapping, SisReg orchestration
    form_metadata.py         Form metadata service
  sisreg/                    SisReg III HTTP integration
    client.py                Async HTTPX client (login, search, detail)
    parser.py                HTML→domain parsing (selectolax)
    selectors.py             CSS selectors for SisReg pages
    models.py                Domain models (Appointment, Detail, etc.)
  db/
    engine.py                Singleton async engine + session factory
    models.py                SQLAlchemy 2.0 declarative models
    repositories/            Data access (CredentialRepo, UserRepo, RegulationSystemRepo)
  scripts/                   CLI scripts (seed_credentials, export_credentials)
  utils/
    encryption.py            Fernet (AES-128-CBC) for at-rest credential storage
    crypto.py                SHA-256 hashing for SisReg login
    masking.py               PII masking for safe logging
  config.py                  Multiple BaseSettings classes + @lru_cache getters
  logging_config.py          structlog setup (JSON prod, console dev)
  main.py                    FastAPI app, middleware stack, lifespan
```

### Key Architectural Patterns

**Request pipeline**: Every request gets a UUID `X-Request-ID` (from header or generated), bound to structlog contextvars for tracing. Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Cache-Control: no-store`) added on all responses. Latency logged per request.

**Authentication**: Admin endpoints use `X-API-Key` header via `Depends(verify_api_key)` in `deps.py` — timing-safe HMAC comparison against comma-separated `API_KEYS` env var. Compat endpoints use `Authorization` header via separate `verify_compat_auth` to isolate concerns.

**Configuration**: Multiple `BaseSettings` classes (`AppSettings`, `ApiAuthSettings`, `DatabaseSettings`, `CredentialEncryptionSettings`, etc.) each with a `@lru_cache` getter. In tests, use `monkeypatch.setenv()` + `get_*_settings.cache_clear()` to isolate config. Settings validate at instantiation (e.g., Fernet key must be valid base64).

**Encryption**: Credentials stored at rest with Fernet (AES-128-CBC + HMAC) via `encrypt_password()`/`decrypt_password()`. SisReg login uses SHA-256 hash via `hash_password()` (SisReg expects pre-hashed password).

**Error flow**: Custom exceptions (`CredentialNotFoundError`, `SisregLoginError`) for domain errors — caught in route handlers and mapped to appropriate HTTP status codes (503, 502). Global exception handler catches unhandled errors → 500 with request context.

**Rate limiting**: `slowapi.Limiter` with `get_remote_address` key function. Disable in tests via `limiter.enabled = False`.

### Database Layer

SQLAlchemy 2.0 async with asyncpg (PostgreSQL) or aiosqlite (tests):

- **`systems`**: Unified system registry — `system_type` discriminator (regulation/integration). All 6 systems (SISREG, ESUS, SIGA, CARE, SER + Saude AM Digital) in one table.
- **`system_profiles`**: Unified profiles — scope discriminator (regulation/integration/platform) with single `system_id` FK. Platform profiles have no system. CHECK constraint enforces this.
- **`system_endpoints`**: Endpoint catalog with single `system_id` FK. No scope needed — derived from systems.system_type via join.
- **`user_profiles`**: Unified junction — user ↔ system_profiles assignment.
- **`credentials`**: Per-user encrypted credentials with FK to system_profiles. Supports regulation and integration system credentials via profile_id join.

Migrations in `alembic/versions/`. Docker init scripts (`docker/init/`) create reference tables + seed data for local dev.

### Admin UI (Next.js)

Next.js 16 app in `admin/` directory, served on port 3000. Stack: React 19, TypeScript, Tailwind CSS v4, shadcn/ui (base-ui), TanStack Query + Table, Zustand (profile state), next-intl (pt-BR, en-US, es-AR). Pages: dashboard (trigger sync, view status), appointments (table + export), raw data (JSON viewer), reference data, sync history, SisReg console (search/detail), profile settings (videofonista/solicitante). Backend data served via `/api/admin/*` endpoints.

**MANDATORY:** Before ANY admin UI modification, read [ADMIN_FRONTEND_ARCHITECTURE.md](docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md). It defines normative conventions for components, hooks, stores, types, and styling. All new code MUST follow these norms.

```text
admin/
  src/
    app/              Next.js App Router pages (16 routes)
    components/       React components (layout, shared, feature-specific)
    hooks/            TanStack Query hooks (14 hooks)
    lib/              API client, constants, utils, env validation
    providers/        Query, Theme, I18n providers
    stores/           Zustand stores (profile-store)
    types/            TypeScript interfaces (7 type files)
    i18n/             next-intl config
  public/locales/     i18n JSON files (314 keys × 3 languages)
```

Key commands: `pnpm --prefix admin dev`, `pnpm --prefix admin build`, `pnpm --prefix admin lint`, `pnpm --prefix admin test`.

### Testing Patterns

- **Async tests**: `asyncio_mode = "auto"` in `pyproject.toml` — all async test functions run automatically
- **Config isolation**: Use `monkeypatch.setenv("VAR", value)` + `get_*_settings.cache_clear()` in `autouse` fixtures. Always `cache_clear()` in both setup and teardown
- **Route tests**: Create mini FastAPI app with the router under test, use `httpx.AsyncClient(transport=ASGITransport(app=app))`
- **HTTP mocking**: Use `respx` to mock external HTTPX calls (SisReg endpoints)
- **Rate limiter**: Disable in test fixtures via `limiter.enabled = False`, restore in teardown
- **Admin unit/integration tests**: Vitest + jsdom + Testing Library + MSW (Mock Service Worker) for API mocking. Test structure: `admin/tests/unit/`, `admin/tests/integration/`, `admin/tests/mocks/`
- **Admin E2E tests**: Playwright (chromium) in `admin/tests/e2e/`

## Critical Rules

- NEVER log patient data (CPF, CNS, phone, name) in plain text
- NEVER implement a feature without a spec in `docs/specs/features/`
- NEVER change existing behavior without reading existing tests first
- NEVER create list endpoint without pagination (`skip`/`limit`)
- NEVER query inside a loop — use IN clause or JOIN
- NEVER commit outside atomic transaction context (`async with db.begin()`)
- NEVER log PII without masking (`mask_username()`)
- NEVER accept config without semantic validation (`@field_validator`)

## Git Workflow

### Branching Strategy

```text
feature/fix branch → dev → staging → master
```

- **Feature branches** always branch from `master` (unless explicitly told to use `dev` or `staging`)
- **NEVER** commit directly to `dev`, `staging`, or `master`
- **NEVER** push directly to `dev`, `staging`, or `master`
- Always create a feature/fix/chore branch first, then open a PR

### Branch Naming

Use conventional prefixes:

- `feat/<description>` — new features
- `fix/<description>` — bug fixes
- `chore/<description>` — maintenance, tooling, config
- `refactor/<description>` — code restructuring
- `docs/<description>` — documentation changes
- `test/<description>` — test additions/updates

### PR Flow

1. Create branch from `master` → PR to `dev`
2. After review/merge → PR from `dev` to `staging`
3. After validation → PR from `staging` to `master`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: add appointment filtering by procedure code`
- `fix: correct session timeout handling`
- `chore: update pre-commit hooks`
- `refactor: extract phone parsing to utility`

**NEVER** include `Co-Authored-By` or any AI agent attribution in commits, PRs, or descriptions.

### PR Metadata

When creating a PR with `gh pr create`, ALWAYS include:

1. **Label** — map the commit type prefix to its GitHub label:
   - `feat:` → `enhancement`, `fix:` → `bug`, `chore:` → `chore`
   - `refactor:` → `refactor`, `docs:` → `documentation`, `test:` → `test`
   - Add `security` label if the PR touches auth, validation, headers, or PII protection
   - Use `--label` flag (e.g., `--label enhancement --label security`)

2. **Reviewers** — CODEOWNERS handles automatic reviewer assignment. Only add `--reviewer` if the user explicitly requests specific reviewers.

3. **PR body** — follow the PR template (`.github/PULL_REQUEST_TEMPLATE.md`). Fill in all sections.

Example:

```bash
gh pr create --base dev \
  --title "feat: add procedure code filtering" \
  --label enhancement \
  --body "$(cat <<'EOF'
## Summary
...
EOF
)"
```

### Promotion PRs (`promotion-dev-to-master`)

When the user says `promotion-dev-to-master` or `promotion-dev-to-master-y`, execute the full promotion pipeline (dev → staging → master). Read **[docs/workflows/PROMOTION_FLOW.md](docs/workflows/PROMOTION_FLOW.md)** for the complete procedure, templates, and rules.

| Command | dev → staging | staging → master |
|---------|---------------|------------------|
| `promotion-dev-to-master` | auto-merge | **manual** (developer approves and merges) |
| `promotion-dev-to-master-y` | auto-merge | **auto-merge** (full pipeline, no stops) |

Key rules:
- **ALWAYS** use merge commit — **NEVER** squash (preserves history across environments)
- **ALWAYS** include the `promotion` label + all labels from original PRs
- Promotion PRs use a dedicated template (NOT the feature PR template)
- Title format: `promote: {source} to {target} — {summary} (PR #N, #M)`
- staging → master PRs include a **PR Chain** traceability table

## Docker Compose

Primary development environment. Requires `.env` file at project root (see `.env.example` or `.env.docker` for reference). Three services:

- **postgres** (port 5432): PostgreSQL 16 — init scripts in `docker/init/` create reference tables + seed data; Alembic creates tables on API startup
- **api** (port 8000): FastAPI — runs `alembic upgrade head` + seed scripts before startup, hot reload on `src/` changes
- **admin** (port 3000): Next.js Admin UI — dashboard, credentials, system management

After changing init scripts in `docker/init/`, reset the database volume: `docker compose down -v && docker compose up -d`.

## Key References

| What                 | Where                                                         |
|----------------------|---------------------------------------------------------------|
| Business rules       | [BUSINESS_RULES.md](docs/specs/BUSINESS_RULES.md)             |
| Technical spec       | [TECH_SPEC.md](docs/specs/TECH_SPEC.md)                       |
| QA audit report      | [QA_REPORT.md](docs/audit/QA_REPORT.md)                       |
| Feature specs        | [docs/specs/features/](docs/specs/features/)                  |
| **Admin UI architecture** | [ADMIN_FRONTEND_ARCHITECTURE.md](docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md) |
| Promotion flow       | [PROMOTION_FLOW.md](docs/workflows/PROMOTION_FLOW.md)         |
| Postman collection   | [postman/](postman/)                                           |

## Language Policy (Immutable)

All **code** artifacts in **English**. All **documentation** in **Portuguese (pt-BR)**.

**English (mandatory):** source code, comments, commits, branch names, feature names, tags, PR titles/descriptions, log messages, code file names.

**Portuguese pt-BR (mandatory):** docs, specs, business rules, readme.

**Exception:** SisReg domain terms stay in Portuguese as-is (e.g., `Videofonista`, `fichaAmbulatorial`). These are proper domain names — do NOT translate them.

See [CONSTITUTION.md section 6](docs/specs/CONSTITUTION.md) for the full policy.
