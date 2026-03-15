# Relatório de Auditoria QA — regula-hub

**Data:** 2026-03-06
**Escopo:** 816 linhas de código-fonte + suite de testes (46 testes)
**Tipo:** Auditoria completa de segurança, qualidade de código e performance
**Nível de Risco Geral:** MEDIO (mitigado pelo escopo limitado e operações read-only)

---

## Sumário Executivo

O `regula-hub` é um microserviço FastAPI bem estruturado que faz scraping do SisReg III via HTTP direto. A arquitetura demonstra boas práticas (DI, Strategy Pattern, Pydantic). Foram identificados **10 achados de segurança**, **6 code smells** e **6 gaps de cobertura de testes**. As correções HIGH foram implementadas nesta auditoria.

---

## 1. Vulnerabilidades de Segurança

| # | Severidade | Arquivo | Achado | Status |
| --- | --- | --- | --- | --- |
| S1 | **HIGH** | `session.py:66,74,85` | PII em logs — username em plain text | CORRIGIDO |
| S2 | **HIGH** | `operator_service.py:39,42,47,62` | PII em logs — operator.username em 4 locais | CORRIGIDO |
| S3 | **HIGH** | `routes.py:56` | Erro exposto ao cliente no health check — `str(exc)` vaza topologia | CORRIGIDO |
| S4 | **MEDIUM** | `routes.py:60-68` | Sem validacao de input — datas aceitas como string sem regex/range | CORRIGIDO |
| S5 | **MEDIUM** | `main.py:33-37` | CORS `allow_origins=["*"]` — qualquer dominio acessa a API | CORRIGIDO |
| S6 | **MEDIUM** | Toda a API | Sem rate limiting — operacoes pesadas sem throttling | PENDENTE |
| S7 | **MEDIUM** | `session.py:99-104` | Deteccao de sessao fragil via substring match | ADIADO |
| S8 | **LOW** | `config.py:9-10` | Credenciais aceitam string vazia | CORRIGIDO |
| S9 | **LOW** | `config.py:12` | Profile como string em vez de Enum | DOCUMENTADO |
| S10 | **INFO** | Toda a API | Sem autenticacao na API (assumido API Gateway externo) | DOCUMENTADO |

### Detalhes das Correcoes

**S1/S2 — Mascaramento de PII:** Criado `src/regulahub/utils/masking.py` com `mask_username()` que retorna SHA-256 truncado (8 chars hex). Todos os logs de username agora usam hash em vez de texto plano.

**S3 — Health check seguro:** `_check_sisreg_reachable()` agora retorna `detail="Service unavailable"` (generico) e loga o erro real internamente via `logger.exception()`.

**S4 — Validacao de datas:** Endpoint `/appointments` agora valida:
- Formato via regex `^\d{2}/\d{2}/\d{4}$` (Query pattern)
- Valores validos via `datetime.strptime()`
- `end_date >= start_date`
- Range maximo de 365 dias

**S5 — CORS configuravel:** Adicionado `CORS_ORIGINS` em `AppSettings` (default `"*"` para dev). Em producao, setar via env var com origens separadas por virgula.

**S8 — Validacao de config:** `username` e `password` agora exigem `min_length=1`.

---

## 2. Code Smells

| # | Severidade | Arquivo | Achado | Status |
| --- | --- | --- | --- | --- |
| C1 | **MEDIUM** | `appointment_service.py:64` | Violacao de encapsulamento — `self._navigator._strategy` | CORRIGIDO |
| C2 | **LOW** | `operator_service.py` + `appointment_service.py` | Deduplicacao repetida (seen_codes pattern) | PENDENTE |
| C3 | **LOW** | `navigation.py:71` | Magic number `situation="7"` | PENDENTE |
| C4 | **LOW** | `parser.py:118,125,134` | Type hints incompletas | PENDENTE |
| C5 | **LOW** | `navigation.py:33-38` | ValueError generico para erros de navegacao | PENDENTE |
| C6 | **LOW** | `operator_service.py:61` | Catch Exception muito amplo | CORRIGIDO |

### Detalhes das Correcoes

**C1 — Encapsulamento:** Adicionado `SisregNavigator.get_filter_params()` como metodo publico. `AppointmentService` agora usa `self._navigator.get_filter_params()` em vez de acessar `_strategy` diretamente.

**C6 — Catch granular:** `operator_service.py` agora diferencia `LoginError`, `SessionExpiredError` e `Exception` com logs adequados.

---

## 3. Analise Big-O por Endpoint

| Endpoint | Complexidade | Variaveis | Worst-Case | Risco |
| --- | --- | --- | --- | --- |
| `GET /health` | **O(1)** + 1 DB call | Valida conexao + Fernet key | < 1s response time | Baixo |
| `GET /api/admin/credentials` | **O(n)** | n=credenciais cadastradas | Paginado (skip/limit) | Baixo |
| `GET /api/admin/systems` | **O(n)** | n=sistemas cadastrados | Paginado (skip/limit) | Baixo |
| `GET /api/admin/users` | **O(n)** | n=usuarios cadastrados | Paginado (skip/limit) | Baixo |

> **Nota:** Os endpoints de scraping SisReg (`GET /appointments`, `GET /appointments/{code}`, `process_operators()`) foram removidos junto com o pipeline.

---

## 4. Gaps de Cobertura de Testes

| # | Severidade | Gap | Status |
| --- | --- | --- | --- |
| T1 | **HIGH** | Testes de seguranca (PII, health check leak, validacao) | CORRIGIDO — 7 testes novos |
| T2 | **HIGH** | Testes da service layer com erros | PENDENTE |
| T3 | **MEDIUM** | Testes de validacao de datas | CORRIGIDO — 4 testes novos |
| T4 | **MEDIUM** | Testes de paginacao multi-pagina | PENDENTE |
| T5 | **LOW** | Testes para operator_service | PENDENTE |
| T6 | **LOW** | Parser edge cases | PENDENTE |

### Testes Adicionados (11 novos)

- `test_health_check_does_not_leak_error_details`
- `test_no_pii_in_login_logs`
- `test_no_pii_in_operator_logs`
- `test_date_validation_rejects_invalid_format`
- `test_date_validation_rejects_end_before_start`
- `test_date_validation_rejects_range_over_365_days`
- `test_date_validation_rejects_invalid_date_values`
- `test_mask_username_returns_hex_hash`
- `test_mask_username_is_deterministic`
- `test_mask_username_different_inputs_differ`
- `test_mask_username_hides_original`

---

## 5. SAST Pipeline Implementado

### Ferramentas

| Ferramenta | Proposito | Resultado Inicial |
| --- | --- | --- |
| **Bandit** | SAST Python (OWASP) | 0 issues em 816 linhas |
| **Ruff** (regras `S`) | Security lint rapido | 0 issues (apos correcoes) |
| **detect-private-key** | Prevenir commit de chaves | Ativo via pre-commit |
| **pre-commit** | Orquestrador de hooks | Configurado |

### Configuracao

- `.pre-commit-config.yaml` — hooks: detect-private-key, ruff, ruff-format, bandit
- `pyproject.toml` — regras Ruff `S` ativadas, config Bandit adicionada
- Dev dependencies: `pre-commit ^4.0`, `bandit ^1.8`

### Como Usar

```bash
# Instalar hooks (uma vez)
poetry run pre-commit install

# Rodar manualmente
poetry run pre-commit run --all-files

# Bandit standalone
poetry run bandit -c pyproject.toml -r src/
```

---

## 6. Conformidade LGPD

| Requisito | Status | Notas |
| --- | --- | --- |
| Nao logar dados de pacientes (CPF, CNS, telefone) | OK | Nenhum dado de paciente em logs |
| Nao logar credenciais | OK | Senhas nunca logadas; usernames agora mascarados |
| Autenticacao na API | PENDENTE | Depende de API Gateway externo (ptm-auth-server) |
| Minimizacao de dados | OK | API retorna apenas dados necessarios |
| Operacoes read-only | OK | Nenhum endpoint de escrita/cancelamento |

---

## 7. Resumo de Metricas

| Metrica | Antes | Depois |
| --- | --- | --- |
| Testes | 35 | 46 (+11) |
| Issues Bandit | N/A | 0 |
| Issues Ruff (security) | N/A | 0 |
| Achados HIGH corrigidos | 3/3 | 3/3 |
| Achados MEDIUM corrigidos | 3/5 | 3/5 |
| Achados LOW corrigidos | 2/4 | 2/4 |

---

## 8. Itens Pendentes (proximas iteracoes)

### Prioridade Media
- **S6** — Rate limiting com `slowapi`
- **T2** — Testes de retry da service layer com `SessionExpiredError`
- **T4** — Testes de paginacao multi-pagina

### Prioridade Baixa
- **C2** — Extrair helper `deduplicate_by_code()`
- **C3** — Constante nomeada para `situation="7"`
- **C4** — Type hints completas no parser
- **C5** — Custom `SisregNavigationError` exception
- **T5/T6** — Testes para operator_service e parser edge cases

---

## Auditoria V2 — 2026-03-15

**Escopo:** Auditoria completa pós-refactoring (remoção do pipeline SisReg, adição de Admin UI, multi-system schema, credential management).
**Achados:** 63 itens identificados em segurança, performance, observabilidade, testes e infraestrutura.
**Documento normativo derivado:** [BACKEND_GUARDRAILS.md](../specs/BACKEND_GUARDRAILS.md)

### Achados por Categoria

#### Segurança (CRÍTICO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-S1 | Chave Fernet não validada semanticamente no startup | `config.py` | CORRIGIDO | `@field_validator` obrigatório |
| V2-S2 | CORS `allow_headers=["*"]` permite headers arbitrários | `main.py:50` | CORRIGIDO | Lista explícita de headers |
| V2-S3 | Falhas de autenticação sem log (sem IP, sem timestamp) | `api/deps.py` | CORRIGIDO | Logar falhas com IP |
| V2-S4 | Username em plaintext em logs de decriptação | `credential_service.py` | CORRIGIDO | `mask_username()` obrigatório |
| V2-S5 | Frontend `fetch()` sem timeout | `api-client.ts` | CORRIGIDO | `AbortSignal.timeout()` |
| V2-S6 | API key vazia aceita silenciosamente no frontend | `api-client.ts` | CORRIGIDO | Throw se vazia |

#### Banco de Dados e Performance (ALTO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-D1 | N+1 query em `_enrich_credentials` (loop de profile lookups) | `credential_routes.py` | CORRIGIDO | Batch load com IN clause |
| V2-D2 | Endpoints GET sem paginação (`skip`/`limit`) | Todas as route files | CORRIGIDO | Paginação obrigatória |
| V2-D3 | Pool de conexões com defaults do SQLAlchemy (5/10) | `db/engine.py` | CORRIGIDO | Pool via env vars |
| V2-D4 | `db.commit()` fora de transação atômica | `credential_routes.py` | CORRIGIDO | `async with db.begin()` |
| V2-D5 | Schemas de input sem `min_length`/`max_length` | `schemas.py` | CORRIGIDO | Constraints obrigatórias |

#### Observabilidade (ALTO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-O1 | Zero request logging (method, path, status, latency) | `main.py` | CORRIGIDO | Middleware obrigatório |
| V2-O2 | Sem X-Request-ID em requests | `main.py` | CORRIGIDO | Middleware gera/propaga |
| V2-O3 | Exception handler sem contexto (method, path) | `main.py` | CORRIGIDO | Contexto obrigatório |
| V2-O4 | Health check não valida Fernet key | `api/routes.py` | CORRIGIDO | Validar dependências |

#### API Design (MÉDIO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-A1 | Rate limiting registrado mas não aplicado nos endpoints | Todas as route files | CORRIGIDO | `@limiter.limit()` obrigatório |
| V2-A2 | Sem error response padronizado | `main.py`, `schemas.py` | CORRIGIDO | `ErrorResponse` schema |
| V2-A3 | Handler morto de `NotImplementedError` | `main.py` | CORRIGIDO | Removido |

#### Frontend (MÉDIO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-F1 | i18n double-render (import estático + dinâmico) | `layout.tsx`, `i18n-provider.tsx` | CORRIGIDO | Pattern oficial next-intl |
| V2-F2 | Locale change com `window.location.reload()` | `i18n-provider.tsx` | CORRIGIDO | React state management |
| V2-F3 | Mutation errors descartados (onError sem ApiError.detail) | `use-credential-mutations.ts` | CORRIGIDO | Capturar `ApiError.detail` |
| V2-F4 | Form submit sem validação de userId | `credential-form-dialog.tsx` | CORRIGIDO | Desabilitar submit |
| V2-F5 | Cache times hardcoded nos hooks | Múltiplos hooks | CORRIGIDO | Centralizar em constants |

#### Testes e CI/CD (ALTO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-T1 | Coverage 68% (abaixo do threshold de 70%) | `tests/` | PENDENTE | Testar routes sub-cobertas |
| V2-T2 | Sem CI pipeline (GitHub Actions) | `.github/workflows/` | PENDENTE | Criar `ci.yml` |
| V2-T3 | Sem testes de integração para CRUD admin | `tests/integration/` | PENDENTE | Criar testes de integração |

#### Infraestrutura (BAIXO)

| # | Achado | Arquivo | Status | Regra Derivada |
|---|--------|---------|--------|----------------|
| V2-I1 | Docker Compose sem network isolation | `docker-compose.yml` | CORRIGIDO | Networks explícitas |
| V2-I2 | Dependências órfãs (selectolax, tenacity, apscheduler) | `pyproject.toml` | CORRIGIDO | Removidas junto com o pipeline |
| V2-I3 | Sem `.dockerignore` | Raiz do projeto | CORRIGIDO | Criar `.dockerignore` |
| V2-I4 | Sem service layer para systems e users | Routes fazem lógica | PENDENTE | Criar services |

### Resumo de Métricas V2

| Métrica | Status |
|---------|--------|
| Total de achados | 63 |
| Achados CRÍTICO | 6/6 corrigidos |
| Achados ALTO | 9/12 corrigidos |
| Achados MÉDIO | 8/8 corrigidos |
| Achados BAIXO | 3/4 corrigidos |
| Documento normativo | [BACKEND_GUARDRAILS.md](../specs/BACKEND_GUARDRAILS.md) criado |
