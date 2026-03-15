# Plano de Remediacao

**Repositorio:** regula-hub
**Data:** 2026-03-13
**Base:** CODE_SMELLS_REPORT.md + SECURITY_REPORT.md

---

## Estrategia Geral

A remediacao segue o principio de **impacto maximo com esforco minimo**. Priorizamos fixes que:
1. Eliminam riscos de seguranca reais
2. Reduzem duplicacao de codigo critico
3. Previnem falhas silenciosas em producao

---

## Fase 1 — Alta Prioridade (1-2 dias)

Fixes de seguranca e bugs de confiabilidade que afetam producao.

### 1.1 Centralizar resolucao de credenciais

| Campo | Valor |
|-------|-------|
| IDs | CS-01, CS-02 |
| Esforco | ~1h |
| Arquivos | `api/deps.py`, `services/credential_service.py` |

**O que fazer:**
1. Garantir que toda resolucao de credenciais passe pelo `CredentialService`
2. Capturar apenas `SQLAlchemyError` e `ValueError` (nao `Exception` generico)
3. Adaptar os callers para mapear excecoes tipadas para HTTP 503 conforme contexto
4. Atualizar testes existentes

> **Nota:** Apos remocao do pipeline, `worker/pipeline.py` e `raw/routes.py` nao existem mais. A duplicacao foi reduzida naturalmente.

---

### ~~1.2 Robustecer deteccao de sessao expirada~~ (REMOVIDO)

> Arquivos `client/session.py` e `selectors/login.py` removidos junto com o pipeline SisReg. CS-04 e SEC-06 nao se aplicam mais.

---

### 1.3 Rate limiting em validate-credentials

| Campo | Valor |
|-------|-------|
| IDs | SEC-02, SEC-03 |
| Esforco | ~2h |
| Arquivos | `api/controllers/raw/routes.py`, `main.py` (middleware) |

**O que fazer:**
1. Adicionar `slowapi` como dependencia
2. Configurar limiter global: 100 req/min por API key
3. Limiter especifico para `/raw/validate-credentials`: 5 req/min por IP
4. Uniformizar resposta de erro para `not_configured` e `invalid_credentials` (prevenir enumeracao de usuarios)

---

### 1.4 Corrigir exception handling em encryption

| Campo | Valor |
|-------|-------|
| IDs | CS-02 |
| Esforco | ~15min |
| Arquivos | `utils/encryption.py` |

**O que fazer:**
1. `encryption.py`: trocar `(InvalidToken, Exception)` por `(InvalidToken, UnicodeDecodeError)`

> **Nota:** `worker/steps/transform.py` (CS-03) foi removido junto com o pipeline SisReg.

---

## Fase 2 — Media Prioridade (3-5 dias)

Qualidade de codigo e melhorias de UX que reduzem risco operacional.

### ~~2.1 Refatorar raw endpoints (eliminar duplicacao)~~ (REMOVIDO)

> Arquivo `api/controllers/raw/routes.py` removido junto com o pipeline SisReg. CS-05, CS-06, CS-07 nao se aplicam mais.

---

### ~~2.2 Sanitizar mensagens de erro persistidas~~ (REMOVIDO)

> Arquivos `worker/pipeline.py` e `api/controllers/raw/routes.py` removidos junto com o pipeline SisReg. SEC-05 e SEC-10 nao se aplicam mais.

---

### ~~2.3 Mascarar CNES nos logs~~ (REMOVIDO)

> Arquivo `client/session.py` removido junto com o pipeline SisReg. SEC-04 nao se aplica mais.

---

### 2.4 Corrigir wildcard import do Lucide

| Campo | Valor |
|-------|-------|
| IDs | CS-09 |
| Esforco | ~1h |
| Arquivo | `admin/src/components/layout/nav-group.tsx` |

**O que fazer:**
1. Criar `ICON_MAP` com apenas os icones usados no nav
2. Substituir `import * as icons` por imports nomeados
3. Verificar se ha outros wildcard imports no frontend

---

### 2.5 Validar localStorage no i18n

| Campo | Valor |
|-------|-------|
| IDs | CS-12, SEC-07 |
| Esforco | ~30min |
| Arquivo | `admin/src/providers/i18n-provider.tsx` |

**O que fazer:**
```typescript
const raw = localStorage.getItem("regulahub-locale");
const stored = locales.includes(raw as Locale) ? (raw as Locale) : null;
```

---

### 2.6 Resource limits no Docker Compose

| Campo | Valor |
|-------|-------|
| IDs | SEC-08 |
| Esforco | ~30min |
| Arquivo | `docker-compose.yml` |

**O que fazer:** Adicionar `deploy.resources.limits` para api (1GB, 2 CPUs) e postgres (512MB, 1 CPU).

---

## Fase 3 — Baixa Prioridade (1-2 sprints)

Melhorias de qualidade e manutencao a longo prazo.

### 3.1 Extrair logica de componentes para hooks

| Campo | Valor |
|-------|-------|
| IDs | CS-10, CS-11, CS-16 |
| Esforco | ~4h |

**O que fazer:**
1. `useCredentialForm()` — logica de validacao e mutacao
2. `useCredentialDetail()` — view/edit state management
3. `useSisregEndpoint(profile)` — centralizar endpoint resolution
4. `useApiError()` — tratamento de erros padronizado

---

### 3.2 Adicionar testes frontend

| Campo | Valor |
|-------|-------|
| IDs | CS-15 |
| Esforco | ~8h |

**O que fazer:**
1. Configurar vitest + testing-library
2. Testar hooks de mutacao (useCredentials, useTriggerSync)
3. Testar validacao de formularios (credential-form)
4. Testar logica de filtro (sisreg-console)

---

### 3.3 Adicionar pytest-cov com threshold

| Campo | Valor |
|-------|-------|
| Esforco | ~1h |

**O que fazer:**
1. Adicionar `pytest-cov` ao dev dependencies
2. Configurar em `pyproject.toml`: `addopts = "--cov=src/regulahub --cov-fail-under=70"`
3. Gerar relatorio de cobertura no CI

---

### ~~3.4 Validar headers de colunas no parser~~ (REMOVIDO)

> Arquivo `selectors/appointment_list.py` e `parser.py` removidos junto com o pipeline SisReg. CS-08 nao se aplica mais.

---

### 3.5 Memoizar Clock e melhorias de performance frontend

| Campo | Valor |
|-------|-------|
| IDs | CS-13, CS-14, CS-17 |
| Esforco | ~2h |

**O que fazer:**
1. Extrair Clock para componente memoizado
2. Adicionar toast.error() nos catch blocks silenciosos
3. Planejar paginacao server-side para credentials table

---

## Resumo de Prioridades

| Fase | Items ativos | Esforco Total | ROI |
|------|-------------|---------------|-----|
| **Fase 1** | 2 items (1.1, 1.3, 1.4) | ~3h | Alto — elimina riscos de seguranca e falhas silenciosas |
| **Fase 2** | 3 items (2.4, 2.5, 2.6) | ~2h | Medio — qualidade de codigo e reducao de risco operacional |
| **Fase 3** | 4 items (3.1, 3.2, 3.3, 3.5) | ~15h | Baixo-medio — manutencao e cobertura de testes |

> **Nota:** Itens 1.2, 2.1, 2.2, 2.3, 3.4 foram removidos — referenciavam código do pipeline SisReg que não existe mais.

**Ordem de execucao recomendada dentro de cada fase:**
- Fase 1: 1.4 (15min, quick win) → 1.1 (1h) → 1.3 (2h)
- Fase 2: 2.5 (30min) → 2.4 (1h) → 2.6 (30min)
- Fase 3: 3.3 (1h) → 3.5 (2h) → 3.1 (4h) → 3.2 (8h)
