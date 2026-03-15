# Guardrails do Backend — Guia Normativo

> **Audiência:** Humanos e agentes de IA que desenvolvem o backend Python/FastAPI.
> **Status:** Aprovado — todo código novo DEVE seguir estas normas.
> **Última revisão:** 2026-03-15

---

## Sumário

1. [Lições Aprendidas (Auditoria 2026-03-15)](#1-lições-aprendidas-auditoria-2026-03-15)
2. [Normas de Arquitetura por Camada](#2-normas-de-arquitetura-por-camada)
3. [Convenções por Camada](#3-convenções-por-camada)
4. [Checklist para Novas Features (Backend)](#4-checklist-para-novas-features-backend)
5. [Anti-Padrões Proibidos](#5-anti-padrões-proibidos)

---

## 1. Lições Aprendidas (Auditoria 2026-03-15)

Tabela de erros cometidos por agents, causa raiz, e regra derivada:

| Erro | Causa Raiz | Regra Derivada |
|------|-----------|----------------|
| Chave Fernet inválida não detectada no startup | Config valida formato mas não semântica | **REGRA:** Todo campo de config com semântica específica DEVE ter `@field_validator` que testa a semântica (ex: Fernet key, URLs, durations) |
| CORS `allow_headers=["*"]` | Agent copiou exemplo genérico | **REGRA:** CORS headers devem ser lista explícita — NUNCA wildcard |
| Falhas de auth sem log | Agent não pensou em auditoria | **REGRA:** Todo path de autenticação DEVE logar falhas com IP e timestamp |
| Username em plaintext nos logs | Agent usou f-string direta | **REGRA:** Todo dado de usuário em logs DEVE usar `mask_username()` de `utils/masking.py` |
| N+1 queries em loops | Agent resolveu profile por credencial | **REGRA:** Nunca fazer query dentro de loop — usar IN clause ou JOIN |
| Sem paginação nos endpoints | Agent retornou lista completa | **REGRA:** Todo endpoint de listagem DEVE ter `skip`/`limit` com defaults e limites |
| `db.commit()` solto fora de transação | Agent seguiu pattern do SQLAlchemy tutorial | **REGRA:** Toda mutação de DB DEVE usar `async with db.begin()` para atomicidade |
| Pool de conexões subdimensionado | Agent usou defaults do SQLAlchemy | **REGRA:** Pool DEVE ser configurado via env vars com defaults de produção |
| Rate limiting configurado mas não aplicado | Agent registrou middleware sem decorators | **REGRA:** Se um mecanismo de proteção está no código, ele DEVE estar ativo — nunca "placeholder" |
| Zero request logging | Agent não adicionou observabilidade | **REGRA:** Todo request HTTP DEVE gerar log estruturado com method, path, status, latency |
| Sem Request ID | Agent não pensou em tracing | **REGRA:** Todo request DEVE ter `X-Request-ID` (gerado ou recebido) propagado nos logs |
| Input schemas sem constraints | Agent definiu campos sem min/max length | **REGRA:** Todo campo string em schema de input DEVE ter `min_length` e `max_length` |
| API key vazia aceita silenciosamente | Agent usou `?? ""` como fallback | **REGRA:** Credenciais e chaves NUNCA devem ter fallback silencioso — falhar alto |
| Soft-delete vs hard-delete inconsistente | Agents diferentes usaram estratégias diferentes | **REGRA:** Toda entidade usa soft-delete (`is_active`) — hard delete somente para junction tables |
| Business logic em routes | Agent colocou queries direto nos controllers | **REGRA:** Routes são orquestradoras — lógica vai no Service layer, queries no Repository |

---

## 2. Normas de Arquitetura por Camada

### 2.1 Estrutura de Diretórios

```
src/regulahub/
├── api/                    # Camada de apresentação
│   ├── controllers/        # Agrupamento por domínio (admin/, regulation/, raw/)
│   │   └── {domínio}/
│   │       ├── routes.py   # Endpoints — composição PURA (valida, chama service, retorna)
│   │       └── schemas.py  # Pydantic request/response DTOs (NUNCA entities)
│   ├── deps.py             # FastAPI dependencies (auth, session, etc.)
│   ├── rate_limit.py       # slowapi config
│   ├── schemas.py          # Shared schemas (health, error responses)
│   └── routes.py           # Health check e root routes
│
├── services/               # Camada de negócio — TODA lógica aqui
│   └── {domínio}_service.py
│
├── db/                     # Camada de persistência
│   ├── models.py           # SQLAlchemy models (ORM)
│   ├── engine.py           # Engine singleton, session factory
│   ├── statuses.py         # Enums de status
│   └── repositories/       # Data access — queries SQL vão AQUI
│       └── {domínio}.py
│
├── integrations/           # Clientes de APIs externas
│   └── {serviço}_client.py
│
├── utils/                  # Funções puras, sem side effects, sem IO
│   ├── crypto.py
│   ├── encryption.py
│   └── masking.py
│
├── config.py               # Pydantic Settings (todas as configs)
├── logging_config.py       # structlog setup
└── main.py                 # FastAPI app factory
```

### 2.2 Regra de Ouro: Cada Camada Tem Sua Responsabilidade

| Camada | Faz | NÃO faz |
|--------|-----|---------|
| `api/controllers/` | Valida input, chama service, serializa output, HTTP status | Query SQL, lógica de negócio, acesso a ORM |
| `services/` | Orquestra lógica de negócio, aplica regras, chama repos | HTTP direto, parsing HTML, acesso a engine |
| `db/repositories/` | CRUD, queries complexas, flush | Commit (quem comita é o caller), lógica de negócio |
| `db/models.py` | Define schema ORM, relationships, constraints | Lógica de negócio, IO, queries |
| `utils/` | Funções puras (hash, mask, format) | IO, acesso a DB, side effects |
| `config.py` | Carrega e valida env vars | Lógica de negócio, IO além de .env |
| `integrations/` | Chamadas HTTP a serviços externos | Lógica de negócio, acesso a DB |

---

## 3. Convenções por Camada

### 3.1 Config (`config.py`)

**Regra: Toda config com semântica específica DEVE ter validação no startup.**

```python
# ✅ CORRETO — valida semântica da chave Fernet
class CredentialEncryptionSettings(BaseSettings):
    credential_encryption_key: str = Field(..., min_length=44)

    @field_validator("credential_encryption_key")
    @classmethod
    def validate_fernet_key(cls, v: str) -> str:
        try:
            Fernet(v.encode())
        except Exception as exc:
            raise ValueError("Invalid Fernet key") from exc
        return v

# ❌ PROIBIDO — aceita qualquer string de 44 chars sem testar
class CredentialEncryptionSettings(BaseSettings):
    credential_encryption_key: str = Field(..., min_length=44)
```

**Regras adicionais:**
- URLs DEVEM ser validadas com `AnyHttpUrl` do Pydantic ou `urlparse`
- Timeouts DEVEM ser positivos (`gt=0`)
- Credenciais NUNCA devem ter fallback silencioso — se ausentes, falhar no startup
- Pool de DB DEVE ser configurável via env vars com defaults de produção

### 3.2 API Routes (`api/controllers/`)

**Regra: Routes fazem APENAS orquestração — sem SQL, sem lógica de negócio.**

```python
# ✅ CORRETO — route orquestra
@router.post("", response_model=CredentialItem, status_code=201)
async def create_credential(
    body: CredentialCreate,
    db: AsyncSession = Depends(get_session),
) -> CredentialItem:
    service = CredentialService(db)
    credential = await service.create(body)
    return CredentialItem.model_validate(credential)

# ❌ PROIBIDO — lógica de negócio na route
@router.post("")
async def create_credential(body: CredentialCreate, db: AsyncSession = Depends(get_session)):
    existing = await db.execute(select(Credential).where(...))  # SQL direto
    if existing:
        # lógica de negócio...
    data = body.model_dump()
    data["encrypted_password"] = encrypt_password(body.password)  # lógica na route
    await db.commit()  # commit na route
```

**Rate Limiting:** Todo endpoint DEVE ter `@limiter.limit()` decorator.

```python
# ✅ CORRETO
@router.get("")
@limiter.limit("30/minute")
async def list_items(request: Request, ...): ...

# ❌ PROIBIDO — endpoint sem rate limit quando slowapi está configurado
@router.get("")
async def list_items(...): ...
```

**Paginação:** Todo endpoint de listagem DEVE ter `skip`/`limit`.

```python
# ✅ CORRETO
@router.get("", response_model=PaginatedResponse)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
) -> PaginatedResponse: ...

# ❌ PROIBIDO — retornar lista completa sem limites
@router.get("")
async def list_items(db: AsyncSession = Depends(get_session)):
    return await repo.list_all()
```

**Error Response:** Usar schema padronizado `ErrorResponse`.

```python
class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
```

### 3.3 Services (`services/`)

**Regra: Toda mutação DEVE usar transação atômica.**

```python
# ✅ CORRETO — transação atômica
async def create(self, data: CredentialCreate) -> Credential:
    async with self.db.begin():
        existing = await self.repo.find_existing(data)
        if existing:
            raise ConflictError("Already exists")
        credential = await self.repo.create(data.model_dump())
        return credential

# ❌ PROIBIDO — commits soltos
async def create(self, data):
    credential = await self.repo.create(data)
    await self.db.commit()  # commit fora de transação
```

### 3.4 Repositories (`db/repositories/`)

**Regra: Repository NUNCA faz commit — apenas flush.**

```python
# ✅ CORRETO — repository faz flush
async def create(self, data: dict) -> Credential:
    entity = Credential(**data)
    self.db.add(entity)
    await self.db.flush()
    return entity

# ❌ PROIBIDO — commit no repository
async def create(self, data: dict) -> Credential:
    entity = Credential(**data)
    self.db.add(entity)
    await self.db.commit()  # NUNCA aqui
```

**N+1 Prevention:** NUNCA fazer query dentro de loop.

```python
# ✅ CORRETO — batch load
profile_ids = [c.profile_id for c in credentials]
profiles = await self.db.execute(
    select(SystemProfile).where(SystemProfile.id.in_(profile_ids))
)
profile_map = {p.id: p for p in profiles.scalars()}

# ❌ PROIBIDO — query por iteração
for cred in credentials:
    profile = await self.db.execute(
        select(SystemProfile).where(SystemProfile.id == cred.profile_id)
    )
```

### 3.5 Models (`db/models.py`)

**Regra: Toda entidade DEVE ter soft-delete e audit fields.**

```python
# ✅ CORRETO
class MyEntity(Base):
    __tablename__ = "my_entities"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
```

**Exceção:** Junction tables (muitos-para-muitos) podem usar hard delete.

### 3.6 Schemas de Input

**Regra: Todo campo string DEVE ter `min_length` e `max_length`.**

```python
# ✅ CORRETO
class CredentialCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    state: str | None = Field(None, min_length=2, max_length=2)

# ❌ PROIBIDO — string sem constraints
class CredentialCreate(BaseModel):
    username: str
    password: str
```

### 3.7 Logging

**Regra: Usar structlog, NUNCA logar PII sem máscara.**

```python
# ✅ CORRETO
import structlog
from regulahub.utils.masking import mask_username

logger = structlog.get_logger()

logger.warning("Decryption failed", user_hash=mask_username(cred.username))

# ❌ PROIBIDO
logger.warning(f"Failed to decrypt password for {cred.username}")
```

**Request ID:** Todo request DEVE ter `X-Request-ID` propagado nos logs via structlog contextvars.

### 3.8 Observabilidade

**Regra: Todo request HTTP DEVE gerar log estruturado.**

```python
# Middleware obrigatório em main.py
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    start = time.monotonic()
    response = await call_next(request)
    latency = round((time.monotonic() - start) * 1000, 2)
    logger.info(
        "request completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency,
    )
    response.headers["X-Request-ID"] = request_id
    return response
```

---

## 4. Checklist para Novas Features (Backend)

Antes de criar qualquer nova feature ou endpoint, verifique:

### Antes de Codar

- [ ] Existe spec em `docs/specs/features/`?
- [ ] Li `BACKEND_GUARDRAILS.md` e `CONSTITUTION.md`?
- [ ] Identifiquei se posso reutilizar services/repos existentes?

### Estrutura

- [ ] Route faz APENAS orquestração (sem SQL, sem lógica)?
- [ ] Lógica de negócio está no Service layer?
- [ ] Queries estão no Repository?
- [ ] Repository NÃO faz commit (apenas flush)?

### Segurança e Validação

- [ ] Schemas de input têm `min_length`/`max_length` em todos os campos string?
- [ ] Endpoint de listagem tem paginação (`skip`/`limit`)?
- [ ] Rate limiting aplicado (`@limiter.limit`)?
- [ ] Credenciais/chaves sem fallback silencioso?

### Dados

- [ ] Service tem transação atômica (`async with db.begin()`)?
- [ ] Nenhuma query dentro de loop (N+1)?
- [ ] Soft-delete para entidades (`is_active`)?

### Observabilidade

- [ ] Logs usam structlog sem PII?
- [ ] Falhas de autenticação são logadas com IP?
- [ ] Exception handlers têm contexto (method, path)?

### Testes

- [ ] Testes cobrem path de sucesso E de erro?
- [ ] Coverage não caiu abaixo de 70%?
- [ ] Testes de integração para fluxos críticos?

---

## 5. Anti-Padrões Proibidos

### Código

| Anti-Padrão | Motivo | Alternativa |
|-------------|--------|-------------|
| `await db.commit()` fora de `async with db.begin()` | Sem atomicidade, inconsistência em caso de erro | `async with db.begin()` no Service |
| Query dentro de loop (`for x: await db.execute(...)`) | N+1 — performance catastrófica com muitos registros | `IN` clause ou `JOIN` para batch load |
| `allow_headers=["*"]` no CORS | Permite headers arbitrários, risco de segurança | Lista explícita: `["X-API-Key", "Content-Type", ...]` |
| `logger.warning(f"Failed for {username}")` | Expõe PII nos logs | `mask_username()` de `utils/masking.py` |
| Schema de input sem `min_length`/`max_length` | Aceita strings arbitrárias, risco de injection/DoS | `Field(..., min_length=1, max_length=100)` |
| Endpoint de listagem sem `skip`/`limit` | Retorna dataset inteiro, risco de OOM | `Query(0, ge=0)` / `Query(50, ge=1, le=200)` |
| Fallback silencioso para credenciais (`key or ""`) | Mascara erro de configuração, falha silenciosa | `Field(..., min_length=1)` — falhar no startup |
| Config semântica sem `@field_validator` | Aceita valores sintaticamente válidos mas semanticamente incorretos | Validar com `Fernet()`, `urlparse()`, etc. |
| `slowapi` registrado mas sem `@limiter.limit()` | Rate limiting é placeholder, não protege nada | Decorator em TODO endpoint |
| Lógica de negócio em routes | Viola separação de camadas, dificulta teste e reuso | Mover para Service layer |

### Arquitetura

| Anti-Padrão | Motivo | Alternativa |
|-------------|--------|-------------|
| Repository faz `commit()` | Quem controla transação é o caller (Service), não o repo | Apenas `flush()` no repository |
| Service acessa `engine` diretamente | Viola encapsulamento da camada de persistência | Receber `AsyncSession` via DI |
| Route faz `select()` ou `insert()` | SQL na camada de apresentação | Delegar para Repository via Service |
| Endpoint sem rate limiting quando `slowapi` está configurado | Mecanismo de proteção inativo | Adicionar `@limiter.limit()` |
| Handler de exceção sem contexto | Impossível diagnosticar erros em produção | Logar `method`, `path`, `remote_addr` |
| Health check que não valida dependências | Retorna "healthy" quando DB está down | Validar TODAS as dependências críticas |
| Middleware registrado mas sem efeito | Código morto que confunde devs | Remover ou ativar completamente |

---

## Referência Rápida — Onde Colocar Cada Coisa

```
"Preciso de um novo endpoint"           → api/controllers/{domínio}/routes.py
"Preciso de schemas de request/response" → api/controllers/{domínio}/schemas.py
"Preciso de lógica de negócio"          → services/{domínio}_service.py
"Preciso de queries SQL"                → db/repositories/{domínio}.py
"Preciso de um modelo ORM"             → db/models.py
"Preciso de uma função utilitária pura" → utils/{nome}.py
"Preciso de config/env vars"            → config.py (com @field_validator se semântica)
"Preciso chamar API externa"            → integrations/{serviço}_client.py
"Preciso de constantes/enums"           → db/statuses.py ou config.py
"Preciso de request/response logging"   → main.py (middleware)
```
