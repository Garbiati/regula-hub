# Spec: Database Layer (sisreg_* tables)

## Contexto

O regula-hub precisa de persistência para armazenar os dados extraídos do SisReg e rastrear o pipeline de integração com o Saúde Digital. As tabelas usam o prefixo `sisreg_` para suportar múltiplos sistemas reguladores no mesmo banco PostgreSQL. Tabelas agnósticas de sistema (sources, projects, regulation_systems, scrappers) não possuem prefixo.

## Requisitos

### Tabelas Novas

#### sisreg_sync_executions
Registro de cada execução do pipeline de sincronização (audit trail).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| reference_date | DATE | Sim | — | Data de referência do sync |
| started_at | TIMESTAMPTZ | Sim | NOW() | Início da execução |
| finished_at | TIMESTAMPTZ | Não | — | Fim da execução |
| status | VARCHAR(20) | Sim | 'running' | running, completed, failed |
| total_listed | INT | Não | 0 | Agendamentos listados |
| total_details_fetched | INT | Não | 0 | Detalhes obtidos |
| total_transformed | INT | Não | 0 | Transformados |
| total_integrated | INT | Não | 0 | Integrados |
| total_reminders_sent | INT | Não | 0 | Lembretes enviados |
| total_errors | INT | Não | 0 | Erros |
| error_summary | TEXT | Não | — | Resumo de erros |
| created_at | TIMESTAMPTZ | Sim | NOW() | Timestamp de criação |

#### sisreg_raw_appointments
Dados brutos extraídos do SisReg (listing JSON + detail JSON).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| sync_execution_id | UUID | Sim | — | FK → sisreg_sync_executions |
| regulation_code | VARCHAR(20) | Sim | — | Código da solicitação |
| reference_date | DATE | Sim | — | Data de referência |
| listing_json | JSONB | Sim | — | JSON do listing |
| detail_json | JSONB | Não | — | JSON do detalhe |
| detail_fetched_at | TIMESTAMPTZ | Não | — | Quando o detalhe foi obtido |
| created_at | TIMESTAMPTZ | Sim | NOW() | Timestamp de criação |
| **UNIQUE** | (reference_date, regulation_code) | | | Garante idempotência |

#### sisreg_appointments
Agendamentos processados (entidade de negócio principal).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| raw_appointment_id | UUID | Não | — | FK → sisreg_raw_appointments |
| regulation_code | VARCHAR(20) | Sim | — | Código da solicitação |
| confirmation_key | VARCHAR(50) | Sim | — | Chave de confirmação |
| reference_date | DATE | Sim | — | Data de referência |
| appointment_date | VARCHAR(10) | Sim | — | yyyy-MM-dd |
| appointment_time | VARCHAR(5) | Sim | — | HH:mm |
| patient_first_name | VARCHAR(200) | Sim | — | Nome do paciente |
| patient_last_name | VARCHAR(200) | Não | '' | Sobrenome |
| patient_birth_date | VARCHAR(10) | Não | '' | Data nascimento |
| patient_cpf | VARCHAR(11) | Não | '' | CPF |
| patient_cns | VARCHAR(15) | Não | '' | CNS |
| patient_mother_name | VARCHAR(200) | Não | '' | Nome da mãe |
| best_phone | VARCHAR(20) | Não | '' | Telefone |
| saude_digital_patient_id | UUID | Não | — | ID no Saúde Digital |
| is_new_account | BOOLEAN | Não | FALSE | Conta nova criada |
| procedure_name | VARCHAR(200) | Sim | — | Nome do procedimento |
| speciality_id | INT | Sim | — | ID da especialidade |
| speciality_name | VARCHAR(100) | Sim | — | Nome da especialidade |
| work_scale_id | VARCHAR(50) | Sim | — | ID da escala |
| work_scale_name | VARCHAR(100) | Sim | — | Nome da escala |
| dept_solicitation_name | VARCHAR(200) | Não | '' | Unidade solicitante |
| dept_solicitation_cnes | VARCHAR(7) | Não | '' | CNES solicitante |
| dept_execute_name | VARCHAR(200) | Não | '' | Unidade executante |
| dept_execute_cnes | VARCHAR(7) | Não | '' | CNES executante |
| dept_execute_address | VARCHAR(500) | Não | '' | Endereço executante |
| is_remote | BOOLEAN | Não | FALSE | Atendimento remoto |
| saude_digital_group_id | UUID | Não | — | Group ID no Saúde Digital |
| doctor_execute_name | VARCHAR(200) | Não | '' | Médico executante |
| doctor_execute_id | UUID | Não | — | ID do médico |
| status | VARCHAR(50) | Sim | 'new' | Status da integração |
| integration_error_message | TEXT | Não | — | Mensagem de erro |
| saude_digital_appointment_id | UUID | Não | — | Appointment ID no Saúde Digital |
| created_at | TIMESTAMPTZ | Sim | NOW() | Timestamp de criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| **UNIQUE** | (reference_date, regulation_code) | | | Garante idempotência |

**Índices:**
- `idx_sisreg_appt_status_date` em (status, reference_date)
- `idx_sisreg_appt_regulation_code` em (regulation_code)
- `idx_sisreg_raw_sync` em (sync_execution_id)

### Status de integração (sisreg_appointments.status)
- `new` — transformado, aguardando integração
- `pending_reminder` — paciente registrado + médico vinculado
- `sent_reminder` — lembrete criado no Saúde Digital
- `detail_not_found` — sem detalhe no SisReg
- `procedure_not_found` — procedimento não mapeado
- `department_not_found` — departamento não mapeado
- `doctor_not_found` — médico não encontrado
- `register_patient_error` — falha no registro do paciente
- `send_reminder_error` — falha ao criar lembrete
- `date_in_past` — data do agendamento já passou
- `unknown_error` — erro inesperado

### Tabelas de sistemas reguladores (Python-owned)

#### regulation_systems
Single source of truth para sistemas reguladores (SISREG, ESUS, SIGA, CARE, SER).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| code | VARCHAR(20) | Sim | — | Código único (SISREG, ESUS, etc.) |
| name | VARCHAR(100) | Sim | — | Nome de exibição |
| description | TEXT | Não | — | Descrição longa |
| base_url | VARCHAR(500) | Não | — | URL base do sistema |
| route_segment | VARCHAR(50) | Não | — | Segmento de rota no frontend |
| icon | VARCHAR(50) | Não | — | Ícone Lucide React |
| table_prefix | VARCHAR(20) | Sim | — | Prefixo das tabelas do sistema (imutável, ex: sisreg) |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |

#### regulation_system_profiles
Perfis por sistema regulador (ex: VIDEOFONISTA em SISREG). Renomeada de `system_profiles` na migration 009.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| system_code | VARCHAR(20) | Sim | — | Código do sistema (FK lógica) |
| profile_name | VARCHAR(50) | Sim | — | Nome do perfil |
| description | TEXT | Não | — | Descrição |
| sort_order | INT | Sim | 0 | Ordem de exibição |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (system_code, profile_name) | | | Perfil único por sistema |

#### integration_system_profiles
Perfis por sistema de integração (ex: api_user em SAUDE_AM_DIGITAL). Twin de `regulation_system_profiles` com FK UUID.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| integration_system_id | UUID | Sim | — | FK → integration_systems.id |
| profile_name | VARCHAR(50) | Sim | — | Nome do perfil |
| description | TEXT | Não | — | Descrição |
| sort_order | INT | Sim | 0 | Ordem de exibição |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (integration_system_id, profile_name) | | | Perfil único por sistema |

#### user_regulation_profiles
Junction table: autorização de usuário para perfil de sistema regulador.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| user_id | UUID | Sim | — | FK → users.id (CASCADE) |
| regulation_system_profile_id | UUID | Sim | — | FK → regulation_system_profiles.id |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (user_id, regulation_system_profile_id) | | | Um assignment por par |

#### user_integration_profiles
Junction table: autorização de usuário para perfil de sistema de integração.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| user_id | UUID | Sim | — | FK → users.id (CASCADE) |
| integration_system_profile_id | UUID | Sim | — | FK → integration_system_profiles.id |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (user_id, integration_system_profile_id) | | | Um assignment por par |

### Tabelas de perfis da plataforma (Python-owned)

#### regulahub_profiles
Perfis da plataforma RegulaHub (operator, administrator, etc.). Substitui as colunas `role`/`level` da tabela `users`.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| profile_name | VARCHAR(50) | Sim | — | Nome do perfil (unique) |
| description | TEXT | Não | — | Descrição |
| level | INT | Sim | 0 | Hierarquia (1=operator, 99=administrator) |
| sort_order | INT | Sim | 0 | Ordem de exibição |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |

#### user_regulahub_profiles
Junction table: assignment de usuário a perfil da plataforma.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| user_id | UUID | Sim | — | FK → users.id (CASCADE) |
| regulahub_profile_id | UUID | Sim | — | FK → regulahub_profiles.id |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (user_id, regulahub_profile_id) | | | Um assignment por par |

### Tabela de sistemas de integração (Python-owned)

#### integration_systems
Sistemas de integração — plataformas de destino para dados processados (Saúde AM Digital, etc.).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| code | VARCHAR(30) | Sim | — | Código único (SAUDE_AM_DIGITAL, etc.) |
| name | VARCHAR(100) | Sim | — | Nome de exibição |
| description | TEXT | Não | — | Descrição longa |
| system_type | VARCHAR(50) | Sim | — | Tipo: teleconsultation, scheduling, ehr |
| state | VARCHAR(2) | Não | — | UF (null = nacional) |
| state_name | VARCHAR(50) | Não | — | Nome do estado |
| base_url | VARCHAR(500) | Não | — | URL base dos endpoints |
| icon | VARCHAR(50) | Não | — | Ícone Lucide React |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |

### Tabelas de endpoints (Python-owned)

#### regulation_endpoints
Endpoints de um sistema regulador (login, busca, detalhe, etc.). Protocolo discriminado por coluna `protocol` (REST, SOAP, WEB).

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| regulation_system_id | UUID | Sim | — | FK → regulation_systems.id |
| name | VARCHAR(50) | Sim | — | Identificador: login, search, find_patient |
| protocol | VARCHAR(10) | Sim | — | REST, SOAP, WEB |
| http_method | VARCHAR(10) | Não | — | GET, POST, PUT (null para WEB nav-only) |
| path | VARCHAR(500) | Sim | — | Path relativo |
| base_url_override | VARCHAR(500) | Não | — | Override quando endpoint está em host diferente |
| description | TEXT | Não | — | Descrição |
| config | JSON | Não | — | Metadados do protocolo (selectors, form_fields, headers) |
| sort_order | INT | Sim | 0 | Ordem de exibição |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (regulation_system_id, name) | | | Endpoint único por sistema |

#### integration_endpoints
Endpoints de um sistema de integração. Mesma estrutura que `regulation_endpoints`, com FK diferente.

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| id | UUID | Sim | gen_random_uuid() | PK |
| integration_system_id | UUID | Sim | — | FK → integration_systems.id |
| name | VARCHAR(50) | Sim | — | Identificador: register_patient, find_patient |
| protocol | VARCHAR(10) | Sim | — | REST, SOAP, WEB |
| http_method | VARCHAR(10) | Não | — | GET, POST, PUT |
| path | VARCHAR(500) | Sim | — | Path relativo |
| base_url_override | VARCHAR(500) | Não | — | Override quando endpoint está em host diferente |
| description | TEXT | Não | — | Descrição |
| config | JSON | Não | — | Metadados do protocolo |
| sort_order | INT | Sim | 0 | Ordem de exibição |
| is_active | BOOLEAN | Sim | TRUE | Ativo/inativo |
| created_at | TIMESTAMPTZ | Sim | NOW() | Criação |
| updated_at | TIMESTAMPTZ | Não | — | Última atualização |
| created_by | UUID | Não | — | Usuário que criou |
| updated_by | UUID | Não | — | Usuário que atualizou |
| **UNIQUE** | (integration_system_id, name) | | | Endpoint único por sistema |

### Tabelas de referência SisReg (Docker init)
Tabelas de referência criadas pelo Docker init (originalmente do .NET, agora Python-owned):
- `sisreg_procedures` — mapeamento de procedimentos
- `sisreg_departments` — departamentos
- `sisreg_department_execution_mappings` — mapeamentos de execução (view)

Carregadas uma vez e cacheadas em memória via `ReferenceDataRepository`.

## Tecnologia
- **ORM:** SQLAlchemy 2.0 async + asyncpg
- **Migrações:** Alembic (async-aware)
- **Banco:** Mesmo PostgreSQL do regulation-service

## Estrutura de diretórios
```
src/regulahub/db/
    __init__.py
    engine.py            # async engine + session factory
    models.py            # SQLAlchemy declarative models (sisreg_* tables)
    repositories/
        __init__.py
        sync_execution.py
        raw_appointment.py
        appointment.py
        reference_data.py  # Leitura das tabelas do .NET
alembic/
    env.py
    versions/
        001_create_sisreg_tables.py
alembic.ini
```

## Critérios de aceitação
1. `alembic upgrade head` cria as 3 tabelas `sisreg_*` com índices
2. Repositories têm operações CRUD com testes unitários
3. reference_data carrega tabelas do .NET em cache
4. Todos os testes passam com banco de teste
