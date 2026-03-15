# Relatorio de Seguranca

**Repositorio:** regula-hub
**Data:** 2026-03-13
**Escopo:** Backend Python (FastAPI) + Frontend Admin (Next.js) + Infraestrutura Docker

---

## Resumo

| Severidade | Quantidade |
|------------|-----------|
| Critica    | 0         |
| Alta       | 3         |
| Media      | 2         |
| Baixa      | 3         |
| Positivo   | 6         |

> **Nota:** SEC-04, SEC-05, SEC-06 e SEC-10 foram removidos — referenciavam código do pipeline SisReg (worker/pipeline.py, client/session.py, raw/routes.py) que não existe mais.

---

## Controles Positivos Encontrados

Antes dos achados negativos, e importante documentar os controles de seguranca **bem implementados**:

1. **Timing-safe API key comparison** — `api/deps.py:19` usa `hmac.compare_digest()` para prevenir timing attacks
2. **Protecao SSRF em PDF** — `utils/pdf.py:26` bloqueia carregamento de recursos externos
3. **PII masking** — `utils/masking.py` mascara username com SHA-256 truncado em todos os logs
4. **Encrypted credentials at rest** — Fernet (AES-128-CBC + HMAC) para senhas no banco
5. **Security headers** — X-Content-Type-Options, X-Frame-Options, HSTS, Cache-Control configurados
6. **Pre-commit SAST** — Bandit + Gitleaks + Ruff security rules rodando em cada commit

---

## Vulnerabilidades

### SEC-01 — API Key Exposta no Bundle Client-Side (NEXT_PUBLIC)

| Campo | Valor |
|-------|-------|
| Severidade | **Alta** |
| Arquivo | `admin/src/lib/api-client.ts:10` |
| CWE | CWE-200 (Information Exposure) |

**Descricao:** A API key e carregada de `NEXT_PUBLIC_API_KEY`, que o Next.js embute no JavaScript do bundle client-side. Qualquer usuario com acesso ao admin UI pode extrair a chave via DevTools > Sources.

```typescript
// admin/src/lib/api-client.ts:10
this.apiKey = process.env.NEXT_PUBLIC_API_KEY ?? "";
```

**Cenario de Exploracaco:** Atacante acessa o admin UI (mesmo sem autenticacao), inspeciona o bundle JS, extrai a API key e faz requisicoes diretas ao backend FastAPI.

**Mitigacao atual:** O admin UI roda em rede interna (Docker port 3000) — superficie de ataque limitada.

**Recomendacao:**
- **Curto prazo:** Aceitar o risco se admin e acessivel apenas via VPN/rede interna
- **Medio prazo:** Mover chamadas para Next.js API Routes (server-side), onde a key fica no servidor
- **Longo prazo:** Implementar autenticacao real no admin UI (OAuth2 via ptm-auth-server)

---

### SEC-02 — Sem Rate Limiting nos Endpoints Admin

| Campo | Valor |
|-------|-------|
| Severidade | **Alta** |
| Arquivos | `src/regulahub/api/controllers/admin/credential_routes.py`, todos endpoints `/api/admin/*` |
| CWE | CWE-770 (Allocation of Resources Without Limits) |

**Descricao:** Endpoints admin possuem protecao por API key mas nenhum rate limiting. Uma chave comprometida permite volume ilimitado de requests.

**Cenario de Exploracaco:** Atacante com API key valida faz brute-force de usernames em `/raw/validate-credentials`, testando credenciais SisReg em massa.

**Recomendacao:**
- Adicionar rate limiting global via middleware (e.g., `slowapi` ou `fastapi-limiter`)
- Limite especifico para `/raw/validate-credentials`: max 5 req/min por IP
- Limite global: 100 req/min por API key

---

### SEC-03 — Validate Credentials Sem Rate Limiting

| Campo | Valor |
|-------|-------|
| Severidade | **Alta** |
| Arquivo | `src/regulahub/api/controllers/raw/routes.py:161-191` |
| CWE | CWE-307 (Improper Restriction of Excessive Authentication Attempts) |

**Descricao:** O endpoint `POST /raw/validate-credentials` aceita um username, busca a senha no banco, e tenta login no SisReg. Sem rate limiting, permite enumerar usuarios validos e testar credenciais.

**Cenario de Exploracaco:**
1. Atacante com API key envia requests variando `username`
2. Resposta `"error": "not_configured"` vs `"error": "invalid_credentials"` revela quais usuarios existem
3. Para usuarios configurados, o login SisReg e executado — potencialmente bloqueando a conta no SisReg por excesso de tentativas

**Recomendacao:**
- Rate limit: max 5 req/min por IP neste endpoint
- Resposta uniforme para `not_configured` e `invalid_credentials` (prevenir enumeracao)
- Log com alerta para volume anomalo de validacoes

---

### ~~SEC-04 — CNES Logado em Plaintext~~ (REMOVIDO)

> Arquivo `client/session.py` removido junto com o pipeline SisReg. Login SisReg com log de CNES nao existe mais.

---

### ~~SEC-05 — Exception Message Pode Conter Dados de Credencial~~ (REMOVIDO)

> Arquivo `worker/pipeline.py` removido junto com o pipeline SisReg. O risco de persistir `str(exc)` com dados sensiveis nao se aplica mais.

---

### ~~SEC-06 — Deteccao de Sessao por Substring (Security-Critical)~~ (REMOVIDO)

> Arquivo `client/session.py` removido junto com o pipeline SisReg. Deteccao de sessao expirada nao se aplica mais.

---

### SEC-07 — Dynamic Import Path no i18n (Path Traversal Potencial)

| Campo | Valor |
|-------|-------|
| Severidade | **Media** |
| Arquivo | `admin/src/providers/i18n-provider.tsx:27` |
| CWE | CWE-22 (Improper Limitation of a Pathname to a Restricted Directory) |

**Descricao:** Import dinamico com variavel do localStorage:
```typescript
import(`../../public/locales/${locale}.json`)
```
Apesar de `locale` vir de localStorage (client-side, sem input externo), a falta de validacao do enum permite que um valor injetado no localStorage (via XSS ou extensao maliciosa) tente carregar paths arbitrarios.

**Mitigacao:** Webpack/Next.js limita imports dinamicos ao diretorio especificado.

**Recomendacao:** Validar `locale` contra `locales` array antes do import.

---

### SEC-08 — Docker Sem Resource Limits

| Campo | Valor |
|-------|-------|
| Severidade | **Media** |
| Arquivo | `docker-compose.yml` |
| CWE | CWE-400 (Uncontrolled Resource Consumption) |

**Descricao:** Nenhum servico no docker-compose tem `mem_limit` ou `cpus` configurados. Em ambiente compartilhado, um servico pode consumir toda a memoria do host.

**Recomendacao:**
```yaml
api:
  deploy:
    resources:
      limits:
        memory: 1024M
        cpus: "2.0"
postgres:
  deploy:
    resources:
      limits:
        memory: 512M
```

---

### SEC-09 — Sem CSRF Protection no Admin

| Campo | Valor |
|-------|-------|
| Severidade | **Baixa** |
| Arquivo | `admin/src/lib/api-client.ts` |
| CWE | CWE-352 (Cross-Site Request Forgery) |

**Descricao:** Requests POST/PUT/DELETE nao incluem CSRF token. Porem, como autenticacao e via header `X-API-Key` (nao cookies), CSRF classico nao se aplica — browsers nao incluem headers customizados em cross-origin requests.

**Status:** Risco baixo por design (API key em header, nao cookie). Documentar como decisao consciente.

---

### ~~SEC-10 — Operator CNES na Mensagem de Erro HTTP~~ (REMOVIDO)

> Arquivo `api/controllers/raw/routes.py` removido junto com o pipeline SisReg.

---

### SEC-11 — Fernet Key Cacheada Indefinidamente

| Campo | Valor |
|-------|-------|
| Severidade | **Baixa** |
| Arquivo | `src/regulahub/utils/encryption.py:8-13` |
| CWE | CWE-798 (Use of Hard-coded Credentials) |

**Descricao:** `@lru_cache` em `_get_fernet()` cacheia a chave de criptografia para sempre. Se a key precisar ser rotacionada, requer restart do processo.

**Status:** Aceitavel para o ciclo de vida atual. Documentar que rotacao de key requer restart.

---

### SEC-12 — Username Exposto na Credentials Table

| Campo | Valor |
|-------|-------|
| Severidade | **Baixa** |
| Arquivo | `admin/src/components/credentials/credentials-table.tsx` |
| CWE | CWE-200 |

**Descricao:** Username SisReg exibido em fonte monospace na tabela do admin. Se a tela for compartilhada, credenciais ficam visiveis.

**Recomendacao:** Mascarar por padrao, com botao "reveal" que requer confirmacao.
