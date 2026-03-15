# Engineering Guidelines

**Repositorio:** regula-hub
**Data:** 2026-03-13
**Objetivo:** Prevenir reincidencia dos problemas documentados em CODE_SMELLS_REPORT.md e SECURITY_REPORT.md

---

## 1. Exception Handling

### Regras

- **NUNCA** usar `except Exception:` com `logger.debug()`. Se o erro e importante o suficiente para capturar, e importante o suficiente para logar com `warning` ou `error`
- **NUNCA** capturar `Exception` junto com subclasses especificas no mesmo except. `except (SpecificError, Exception)` torna `SpecificError` redundante
- **SEMPRE** capturar excecoes especificas. Mapear as excecoes esperadas de cada call site:
  - SQLAlchemy: `SQLAlchemyError`, `IntegrityError`, `OperationalError`
  - HTTPX: `httpx.HTTPError`, `httpx.TimeoutException`
  - Cryptography: `InvalidToken`, `UnicodeDecodeError`
  - Aplicacao: `CredentialNotFoundError`, `DecryptionError`
- **SEMPRE** re-raise ou retornar valor de fallback explicito — nunca `pass` silencioso em catch de erro

### Exemplo

```python
# ERRADO
try:
    creds = await resolve_credentials("videofonista")
except Exception:
    logger.debug("Failed")  # O que falhou? Banco? Decriptografia? Config?

# CERTO
try:
    creds = await resolve_credentials("videofonista")
except CredentialNotFoundError:
    raise HTTPException(503, "No credentials configured")
except DecryptionError:
    logger.error("Credential decryption failed — check CREDENTIAL_ENCRYPTION_KEY")
    raise HTTPException(503, "Credential configuration error")
```

---

## 2. Secure Coding

### Dados Sensiveis em Logs

- **NUNCA** logar em plaintext: CPF, CNS, nome de paciente, telefone, CNES, username SisReg, senha, tokens
- **SEMPRE** usar `mask_username()` para usernames e mascarar CNES (ultimos 3 digitos apenas)
- **NUNCA** persistir `str(exc)` diretamente no banco — sanitizar URLs e parametros primeiro
- Mensagens de erro HTTP **NUNCA** devem confirmar existencia de recursos internos (e.g., "CNES X not found" → "No matching operator found")

### Enumeracao de Usuarios

- Endpoints de validacao de credenciais devem retornar resposta uniforme para "nao configurado" e "invalido"
- Rate limiting obrigatorio em qualquer endpoint que aceite username/credencial como input

### Client-Side

- **NUNCA** usar `NEXT_PUBLIC_` para secrets (API keys, tokens). Usar API Routes do Next.js como proxy
- **SEMPRE** validar valores do `localStorage` contra enum/array de opcoes validas antes de usar
- **NUNCA** usar `as TypeX` para cast de dados externos sem validacao runtime (Zod ou check manual)

### Dependencies

- Credentials no banco: Fernet encrypted, key em env var
- `.env` NUNCA no git (ja configurado em `.gitignore`)
- Pre-commit hooks obrigatorios: ruff, bandit, gitleaks, detect-private-key

---

## 3. Regras de Arquitetura

### Camadas (Backend Python)

```
api/          → Recebe requests, valida input, delega para services
services/     → Orquestra logica de negocio (credenciais, sistemas)
db/           → SQLAlchemy models e repositories (unico ponto de acesso ao banco)
utils/        → Funcoes puras sem estado (crypto, masking, encryption)
```

### Regras de Dependencia

- `api/` pode importar `services/`, `db/`, `utils/`
- `services/` pode importar `db/`, `utils/`
- `utils/` **NAO** pode importar de nenhum outro modulo da aplicacao (exceto `config.py`)

### Regras de Duplicacao

- Se uma logica aparece em 2+ locais, deve ser extraida para `utils/` ou um modulo compartilhado
- Exemplos concretos deste repo:
  - Resolucao de credenciais → `services/credential_service.py`
  - Encryption/decryption → `utils/encryption.py`

---

## 4. Naming Conventions

### Python (Backend)

| Item | Convencao | Exemplo |
|------|-----------|---------|
| Modulos | snake_case | `appointment_service.py` |
| Classes | PascalCase | `AppointmentService`, `SisregSession` |
| Funcoes/metodos | snake_case | `parse_appointment_list()` |
| Constantes | UPPER_SNAKE_CASE | `_MAX_CONCURRENT_OPERATORS` |
| Funcoes privadas | prefixo `_` | `_build_listing_params()` |
| Excecoes | PascalCase + Error/Exception | `SessionExpiredError` |

### TypeScript (Frontend)

| Item | Convencao | Exemplo |
|------|-----------|---------|
| Componentes | PascalCase | `CredentialFormDialog` |
| Hooks | camelCase com prefixo `use` | `useCredentials()` |
| Tipos/Interfaces | PascalCase | `SisregAppointment` |
| Constantes | UPPER_SNAKE_CASE | `SISREG_PROFILE_ENDPOINTS` |
| Arquivos de componente | kebab-case | `credential-form-dialog.tsx` |
| Arquivos de hook | kebab-case com prefixo `use-` | `use-credentials.ts` |

### Idioma

- **Codigo, comentarios, commits, logs, nomes de branch:** Ingles
- **Documentacao, specs, regras de negocio:** Portugues (pt-BR)
- **Excecao:** Termos de dominio SisReg ficam em portugues as-is (`Videofonista`, `fichaAmbulatorial`, `Solicitante`)

---

## 5. Code Review Checklist

Ao revisar um PR, verificar:

### Seguranca
- [ ] Nenhum dado sensivel (CPF, CNS, nome, telefone, CNES) em logs ou respostas HTTP
- [ ] Exception messages nao contem credenciais ou URLs com parametros
- [ ] Inputs externos validados (regex em Path/Query params, Zod no frontend)
- [ ] Sem `NEXT_PUBLIC_` para secrets
- [ ] Sem `except Exception: pass` ou `except Exception: logger.debug()`

### Qualidade
- [ ] Metodos com menos de 50 linhas (extrair se necessario)
- [ ] Sem duplicacao de logica (verificar se funcao similar ja existe em `utils/` ou `services/`)
- [ ] Excecoes tipadas e especificas (nao `Exception` generico)
- [ ] Testes cobrindo happy path e pelo menos 1 error path

### Arquitetura
- [ ] Dependencias seguem a hierarquia de camadas (Secao 3)
- [ ] Novos endpoints admin com API key validation (`Depends(verify_api_key)`)

### Frontend
- [ ] Sem wildcard imports de bibliotecas de icones
- [ ] Erros exibidos ao usuario (toast), nao apenas `console.error()`
- [ ] Valores do localStorage validados antes de uso
- [ ] Componentes > 200 linhas justificados ou quebrados em sub-componentes

---

## 6. Testing

### Backend Python

- **Framework:** pytest + pytest-asyncio (asyncio_mode = "auto") + respx (HTTP mocking)
- **DB em testes:** SQLite (aiosqlite) — nunca PostgreSQL (testes devem ser rapidos e isolados)
- **Cobertura minima:** 70% (configurar `pytest-cov --cov-fail-under=70`)
- **Testes obrigatorios para cada feature:**
  1. Happy path
  2. Pelo menos 1 error path (input invalido, falha de rede, etc.)
  3. Se envolve banco: teste de idempotencia (executar 2x, verificar resultado unico)

### Frontend Next.js

- **Framework:** vitest + @testing-library/react
- **Prioridade de testes:**
  1. Hooks com logica de negocio (mutacoes, validacoes)
  2. Logica de filtro e transformacao de dados
  3. Componentes de formulario (validacao)

### O que NAO testar

- Getters/setters triviais
- Logica do framework (FastAPI dependency injection, Next.js routing)
- Modelos Pydantic simples (a menos que tenham validators customizados)

---

## 7. Dependency Management

### Regras

- **Poetry** para backend Python, **pnpm** para frontend
- Sempre usar version ranges (`^`) em `pyproject.toml` — nunca fixar versao exata (exceto pre-releases)
- Atualizar dependencias mensalmente — verificar CVEs com `pip-audit` ou `safety`
- Novas dependencias precisam de justificativa: nao adicionar biblioteca para algo que pode ser feito em < 20 linhas
- Preferir stdlib quando possivel (e.g., `hashlib` sobre bibliotecas externas de hashing)

### Monitoramento

- `bandit` roda em cada commit (pre-commit hook)
- `gitleaks` previne commit de secrets
- Configurar `dependabot` ou `renovate` para PRs automaticos de atualizacao de seguranca
