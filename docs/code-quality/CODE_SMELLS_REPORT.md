# Relatorio de Code Smells

**Repositorio:** regula-hub
**Data:** 2026-03-13
**Escopo:** Backend Python (FastAPI) + Frontend Admin (Next.js)

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| Alta       | 2         |
| Media      | 4         |
| Baixa      | 2         |

> **Nota:** CS-03, CS-04, CS-05, CS-06, CS-07, CS-08 foram removidos — referenciavam código do pipeline SisReg (worker/, client/, selectors/, api/controllers/raw/) que não existe mais.

---

## Achados — Backend Python

### CS-01 — Resolucao de Credenciais Duplicada

| Campo | Valor |
|-------|-------|
| Arquivos | `src/regulahub/api/deps.py` |
| Impacto | **Medio** — apos remocao do pipeline e raw routes, duplicacao reduzida |
| Problema | O padrao DB lookup -> decrypt -> fallback ainda pode se repetir ao adicionar novos endpoints. Manter logica centralizada em `credential_service.py` |

**Recomendacao:** Garantir que toda resolucao de credenciais passe pelo `CredentialService`.

---

### CS-02 — Broad Exception Handling Suprime Erros Reais

| Campo | Valor |
|-------|-------|
| Arquivos | `src/regulahub/api/deps.py`, `src/regulahub/utils/encryption.py` |
| Impacto | **Alto** — erros de banco, rede ou configuracao sao silenciados |
| Problema | `except Exception:` com `logger.debug()` engole falhas de conexao e ORM errors. Em `encryption.py`, `except (InvalidToken, Exception)` torna `InvalidToken` redundante e mascara qualquer erro como ValueError |

**Recomendacao:**
- `deps.py`: capturar `sqlalchemy.exc.SQLAlchemyError` e `ValueError` separadamente
- `encryption.py`: capturar apenas `(InvalidToken, UnicodeDecodeError)` — excecoes esperadas do Fernet

---

### ~~CS-03 — Redundant Exception Catch em _link_doctor~~ (REMOVIDO)

> Arquivo `worker/steps/transform.py` removido junto com o pipeline SisReg.

---

### ~~CS-04 — Deteccao de Sessao Expirada por String Fragil~~ (REMOVIDO)

> Arquivo `client/session.py` removido junto com o pipeline SisReg.

---

### ~~CS-05 — Metodo Longo: raw_solicitante_appointments~~ (REMOVIDO)

> Arquivo `api/controllers/raw/routes.py` removido junto com o pipeline SisReg.

---

### ~~CS-06 — Dicionario de Parametros SisReg Duplicado~~ (REMOVIDO)

> Arquivo `api/controllers/raw/routes.py` removido junto com o pipeline SisReg.

---

### ~~CS-07 — Bloco PDF Duplicado~~ (REMOVIDO)

> Arquivo `api/controllers/raw/routes.py` removido junto com o pipeline SisReg.

---

### ~~CS-08 — Magic Numbers em Column Indices~~ (REMOVIDO)

> Arquivo `selectors/appointment_list.py` removido junto com o pipeline SisReg.

---

## Achados — Frontend Admin (Next.js)

### CS-09 — Wildcard Import do Lucide Icons

| Campo | Valor |
|-------|-------|
| Arquivo | `admin/src/components/layout/nav-group.tsx:3` |
| Impacto | **Alto** — `import * as icons from "lucide-react"` impede tree-shaking (~100KB+) |

**Recomendacao:** Criar map explicito de icones usados ou usar import dinamico.

---

### CS-10 — Componentes Grandes com Logica de Negocio

| Campo | Valor |
|-------|-------|
| Arquivos | `credential-form-dialog.tsx` (224 linhas), `credential-detail-dialog.tsx` (348 linhas), `filter-card.tsx` (227 linhas) |
| Impacto | **Medio** — dificeis de testar e manter |

**Recomendacao:** Extrair hooks customizados (`useCredentialForm()`, `useCredentialDetail()`).

---

### CS-11 — Endpoint Profile Duplicado em 3 Locais

| Campo | Valor |
|-------|-------|
| Arquivos | `search-panel.tsx`, `detail-panel.tsx`, `use-sisreg-detail.ts` |
| Impacto | **Medio** — `SISREG_PROFILE_ENDPOINTS[profile]` repetido em 3 arquivos |

**Recomendacao:** Centralizar em funcao helper em `lib/constants.ts`.

---

### CS-12 — localStorage Cast Sem Validacao

| Campo | Valor |
|-------|-------|
| Arquivo | `admin/src/providers/i18n-provider.tsx:20` |
| Impacto | **Medio** — valor invalido no localStorage pode quebrar i18n |
| Problema | `as Locale | null` sem validar se o valor e um locale valido |

**Recomendacao:** Validar contra array de locales antes de usar.

---

### CS-13 — Erros Silenciosos no Console

| Campo | Valor |
|-------|-------|
| Arquivos | `search-panel.tsx:65`, `detail-panel.tsx:53` |
| Impacto | **Baixo** — `console.error()` sem feedback ao usuario |

**Recomendacao:** Adicionar `toast.error()`.

---

### CS-14 — Clock Re-render Global

| Campo | Valor |
|-------|-------|
| Arquivo | `admin/src/components/header.tsx` |
| Impacto | **Baixo** — `setInterval(1s)` causa re-render no header inteiro |

**Recomendacao:** Extrair Clock para componente com `React.memo`.

---

### CS-15 — Zero Testes no Frontend

| Campo | Valor |
|-------|-------|
| Arquivo | `admin/src/` |
| Impacto | **Alto** — vitest configurado, zero testes escritos |

**Recomendacao:** Priorizar testes de hooks de mutacao e validacao de formularios.

---

### CS-16 — Tratamento de Erros Inconsistente no Frontend

| Campo | Valor |
|-------|-------|
| Arquivos | Multiplos componentes em `admin/src/components/` |
| Impacto | **Medio** — mix de `toast.error()`, `console.error()` e nenhum tratamento |

**Recomendacao:** Criar hook `useApiError()` com comportamento padronizado.

---

### CS-17 — Credentials Table Sem Paginacao

| Campo | Valor |
|-------|-------|
| Arquivo | `admin/src/components/credentials/credentials-table.tsx` |
| Impacto | **Baixo** (poucos registros por enquanto) |

**Recomendacao:** Implementar paginacao server-side quando necessario.
