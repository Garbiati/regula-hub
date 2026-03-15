# Diagramas de Arquitetura — regula-hub

Documentação visual da arquitetura do serviço **regula-hub**, uma WebAPI FastAPI para gestão de credenciais e configuração de sistemas de regulação.

---

## 1. Diagrama de Contexto do Sistema

Visão de alto nível (estilo C4 Nível 1) mostrando o RegulaHub e seus sistemas externos.

```mermaid
C4Context
    title Contexto do Sistema — regula-hub

    Person(admin, "Operador Admin", "Acessa Admin UI Next.js")
    SystemDb_Ext(pg, "PostgreSQL 16", "Tabelas de sistemas, credenciais, perfis, usuários")

    System(hub, "regula-hub", "FastAPI — Admin API + gestão de credenciais")

    Rel(admin, hub, "Next.js Admin UI", "porta 3000")
    Rel(hub, pg, "SQLAlchemy 2.0 async", "asyncpg")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

---

## 2. Diagrama de Componentes Internos

Módulos do código-fonte e suas dependências.

```mermaid
graph TB
    subgraph API["api/"]
        routes["routes.py<br/><small>/health</small>"]
        deps["deps.py<br/><small>verify_api_key, get_db</small>"]
        admin_ctrl["controllers/admin/<br/><small>credentials, systems, users</small>"]
        schemas["schemas.py<br/><small>ErrorResponse, paginação</small>"]
    end

    subgraph Services["services/"]
        cred_svc["credential_service.py<br/><small>CredentialService</small>"]
    end

    subgraph DB["db/"]
        models["models.py<br/><small>System, SystemProfile, Credential, UserProfile</small>"]
        repos["repositories/<br/><small>credential, system, user</small>"]
        engine["engine.py<br/><small>async SessionLocal</small>"]
    end

    subgraph Utils["utils/"]
        crypto["crypto.py<br/><small>hash_password (SHA-256)</small>"]
        encryption["encryption.py<br/><small>Fernet encrypt/decrypt</small>"]
        masking["masking.py<br/><small>mask_username</small>"]
    end

    config["config.py<br/><small>Pydantic Settings</small>"]
    main["main.py<br/><small>FastAPI app + lifespan</small>"]

    %% API layer
    main --> routes & admin_ctrl
    routes --> deps
    admin_ctrl --> deps & schemas & cred_svc

    %% Service layer
    cred_svc --> encryption & masking

    %% DB layer
    deps --> config & engine
    repos --> models & engine
    engine --> config

    %% Styling
    classDef core fill:#bbf,stroke:#333
```

---

## 3. Diagrama de Endpoints da API

Todos os endpoints organizados por controller, com método HTTP e autenticação.

```mermaid
graph LR
    subgraph Public["Públicos (sem autenticação)"]
        H["GET /health<br/><small>Health check + dependências</small>"]
    end

    subgraph Admin["Admin — Credenciais (X-API-Key)"]
        C1["GET /api/admin/credentials<br/><small>Listar credenciais</small>"]
        C2["POST /api/admin/credentials<br/><small>Criar credencial</small>"]
        C3["PUT /api/admin/credentials/{id}<br/><small>Atualizar credencial</small>"]
        C4["DELETE /api/admin/credentials/{id}<br/><small>Remover credencial</small>"]
    end

    subgraph Systems["Admin — Sistemas (X-API-Key)"]
        S1["GET /api/admin/systems<br/><small>Listar sistemas</small>"]
        S2["GET /api/admin/systems/{id}<br/><small>Detalhe do sistema</small>"]
    end

    subgraph Users["Admin — Usuários (X-API-Key)"]
        U1["GET /api/admin/users<br/><small>Listar usuários</small>"]
    end

    Client((API Client))
    Client -->|"sem auth"| Public
    Client -->|"X-API-Key"| Admin
    Client -->|"X-API-Key"| Systems
    Client -->|"X-API-Key"| Users
```

---

## 4. Diagrama do Banco de Dados

Modelo entidade-relacionamento das tabelas de gestão (sistemas, credenciais, perfis, usuários).

```mermaid
erDiagram
    systems {
        UUID id PK
        VARCHAR_100 name
        VARCHAR_20 system_type "regulation | integration"
        VARCHAR_500 base_url "nullable"
        BOOLEAN is_active
        TIMESTAMPTZ created_at
    }

    system_profiles {
        UUID id PK
        UUID system_id FK "nullable"
        VARCHAR_20 scope "regulation | integration | platform"
        VARCHAR_100 name
        VARCHAR_200 description "nullable"
        BOOLEAN is_active
        TIMESTAMPTZ created_at
    }

    system_endpoints {
        UUID id PK
        UUID system_id FK
        VARCHAR_100 name
        VARCHAR_10 method
        VARCHAR_500 path
        VARCHAR_200 description "nullable"
        BOOLEAN is_active
        TIMESTAMPTZ created_at
    }

    user_profiles {
        UUID id PK
        UUID user_id
        UUID profile_id FK
        TIMESTAMPTZ created_at
    }

    credentials {
        UUID id PK
        UUID user_id
        UUID profile_id FK
        VARCHAR_200 username
        TEXT encrypted_password "Fernet AES-128-CBC"
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at "nullable"
    }

    systems ||--o{ system_profiles : "system_id"
    systems ||--o{ system_endpoints : "system_id"
    system_profiles ||--o{ user_profiles : "profile_id"
    system_profiles ||--o{ credentials : "profile_id"
```

**Constraints notáveis:**
- `system_profiles`: CHECK constraint — `scope = 'platform'` implica `system_id IS NULL`
- `credentials`: credenciais Fernet-encrypted por usuário por perfil de sistema
- Tabelas de referência SisReg (`sisreg_procedures`, `sisreg_departments`, `sisreg_department_execution_mapping`) são criadas por scripts Docker init

---

## 5. Diagrama de Fluxo de Requisição

Ciclo de vida de uma requisição à Admin API (exemplo: criação de credencial).

```mermaid
sequenceDiagram
    participant C as Admin UI (Next.js)
    participant R as FastAPI Router
    participant D as deps.py
    participant Svc as CredentialService
    participant DB as PostgreSQL

    C->>R: POST /api/admin/credentials
    R->>D: verify_api_key(X-API-Key)
    D-->>R: OK

    R->>D: get_db()
    D-->>R: AsyncSession

    R->>Svc: create_credential(data)
    Svc->>Svc: encrypt_password(Fernet)
    Svc->>DB: INSERT INTO credentials
    DB-->>Svc: OK
    Svc-->>R: CredentialResponse

    R-->>C: 201 Created (JSON)
```

---

## Legenda

| Símbolo | Significado |
|---------|-------------|
| Linha sólida (`→`) | Dependência direta / chamada |
| `PK` | Chave primária |
| `FK` | Chave estrangeira |
| Tabelas gerenciadas | Criadas/migradas via Alembic |
| Tabelas de referência `sisreg_*` | Criadas por scripts Docker init (seed data) |
