# Worker de Integração — Agendamentos SisReg → Sistema de Integração

## Contexto

O regula-hub possui endpoints de compatibilidade Absens (`/api/compat/absens/`) que funcionam de forma passiva — o consumidor externo (ptm-regulation-service) puxa os dados. Essa abordagem depende do serviço externo e cria acoplamento operacional.

O worker de integração inverte o fluxo: o regula-hub **busca ativamente** agendamentos no SisReg (d+1 a d+7), enriquece com dados demográficos (CADSUS/CadWeb), e **empurra** os dados enriquecidos para o sistema de integração configurado no banco de dados.

## Princípio Arquitetural

Nenhuma referência hardcoded a sistemas específicos. O worker lê a configuração de `systems` + `system_endpoints` do banco para qualquer sistema do tipo `integration`. Os 6 endpoints REST já existem na seed (migration 001) para o sistema configurado.

## Escopo

### Incluso
- Worker async in-process acionado sob demanda via API
- Tela admin `SisReg > Integrations` para disparar e monitorar execuções
- Pipeline: buscar agendamentos → enriquecer → empurrar para sistema alvo
- Histórico de execuções persistido no banco
- Progresso em tempo real via polling

### Excluído (futuro)
- Execução automática diária via scheduler
- Webhook de notificação ao término
- Configuração de endpoints via UI (usa seed do banco)

## Fluxo de Dados

```
Trigger (UI manual)
  ↓
Resolve credenciais VIDEOFONISTA (CredentialRepository)
  ↓
Busca paralela no SisReg por dia (d+1..d+7)
  → SisregClient.search() × N operadores × N dias
  → Deduplicação por code
  ↓
Enriquecimento (detail + CadWeb)
  → _fetch_details_for_codes() × operadores [Semaphore(5)]
  → Cache CadWeb por CNS dentro da sessão
  ↓
Push para sistema de integração (endpoints do DB)
  → Para cada agendamento enriquecido:
    1. find_patient(cns) → GET /api/patients
    2. register_patient(data) ou update_patient(data)
    3. list_doctors() → GET /api/doctors (cache por execução)
    4. find_reminder(patient_id, date) → idempotência
    5. create_reminder(data) → POST /api/reminders
  ↓
Persiste resultado no banco (integration_executions)
```

## Schema do Banco

### Tabela: `integration_executions`

| Coluna | Tipo | Nullable | Descrição |
|--------|------|----------|-----------|
| `id` | UUID | PK | Identificador da execução |
| `integration_system_id` | UUID FK(systems.id) | NÃO | Sistema alvo |
| `status` | VARCHAR(20) | NÃO | `pending`, `running`, `completed`, `failed`, `cancelled` |
| `date_from` | DATE | NÃO | Data inicial do range |
| `date_to` | DATE | NÃO | Data final do range |
| `total_fetched` | INTEGER | SIM | Agendamentos buscados no SisReg |
| `total_enriched` | INTEGER | SIM | Agendamentos enriquecidos |
| `total_pushed` | INTEGER | SIM | Agendamentos enviados com sucesso |
| `total_failed` | INTEGER | SIM | Falhas no envio |
| `error_message` | TEXT | SIM | Mensagem de erro (se falhou) |
| `progress_data` | JSONB | SIM | Dados de progresso em tempo real |
| `started_at` | TIMESTAMPTZ | SIM | Início da execução |
| `completed_at` | TIMESTAMPTZ | SIM | Término da execução |
| `triggered_by` | VARCHAR(50) | SIM | `manual` ou `scheduled` |
| `is_active` | BOOLEAN | NÃO | Soft-delete |
| `created_at` | TIMESTAMPTZ | NÃO | Criação do registro |
| `updated_at` | TIMESTAMPTZ | SIM | Última atualização |
| `created_by` | UUID | SIM | Usuário que criou |
| `updated_by` | UUID | SIM | Usuário que atualizou |

**Índices:** `idx_integ_exec_system`, `idx_integ_exec_status`, `idx_integ_exec_created`

## Endpoints da API

Prefixo: `/api/admin/integrations`
Autenticação: `X-API-Key` (via `Depends(verify_api_key)`)

| Método | Path | Descrição | Rate Limit |
|--------|------|-----------|------------|
| `GET` | `/systems` | Lista sistemas de integração + endpoints | 30/min |
| `POST` | `/execute` | Dispara execução do worker → 202 Accepted | 3/min |
| `GET` | `/executions/{id}/status` | Status em tempo real | 60/min |
| `GET` | `/executions` | Histórico paginado (`skip`/`limit`) | 30/min |
| `POST` | `/executions/{id}/cancel` | Cancela execução em andamento | 5/min |

### Resposta do Trigger (202 Accepted)

```json
{
  "id": "uuid",
  "status": "pending",
  "dateFrom": "2026-03-23",
  "dateTo": "2026-03-29"
}
```

### Resposta de Status

```json
{
  "id": "uuid",
  "status": "running",
  "dateFrom": "2026-03-23",
  "dateTo": "2026-03-29",
  "totalFetched": 45,
  "totalEnriched": 30,
  "totalPushed": 25,
  "totalFailed": 2,
  "progressData": {
    "stage": "pushing",
    "fetchedCount": 45,
    "enrichedCount": 30,
    "pushedCount": 25,
    "failedCount": 2
  },
  "startedAt": "2026-03-22T20:00:00Z",
  "completedAt": null,
  "triggeredBy": "manual"
}
```

## Tela Admin: SisReg > Integrations

### Layout

1. **Cards de sistemas** — mostra sistemas de integração configurados com seus endpoints
2. **Formulário de trigger** — seletor de sistema, date range (default d+1 a d+7), botão executar
3. **Status de execução** — progresso em tempo real com estágios (buscando → enriquecendo → enviando → completo)
4. **Histórico** — tabela paginada com execuções anteriores (data, status, contadores, duração)

### Navegação

Item `Integrations` adicionado como child de SISREG no sidebar, ícone `Plug` (Lucide).

## Modelo de Execução do Worker

- **In-process async task** via `asyncio.create_task()` — não é um processo separado
- **Status em memória** (`dict[UUID, ExecutionProgress]`) para polling de baixa latência
- **Persistência no DB** (`integration_executions`) para histórico e sobrevivência a restarts
- **Graceful degradation** — falha em 1 agendamento não bloqueia os demais
- **Semaphore(5)** — limite de sessões SisReg concorrentes (consistente com compat_service)

## Reuso de Código

| Funcionalidade | Origem | Caminho |
|---------------|--------|---------|
| Resolução de credenciais | `_resolve_all_credentials()` | `services/compat_service.py:253` |
| Busca paralela SisReg | `_search_single_operator_compat()` | `services/compat_service.py:232` |
| Enriquecimento detail+CadWeb | `_enrich_listings()` | `services/compat_service.py:199` |
| Cliente SisReg | `SisregClient` | `sisreg/client.py` |
| Repository de credenciais | `CredentialRepository` | `db/repositories/credential.py` |

## Critérios de Aceite

1. Worker busca agendamentos de teleconsulta no SisReg para range d+1 a d+7
2. Agendamentos são enriquecidos com dados demográficos (CadWeb/CADSUS)
3. Dados enriquecidos são enviados para o sistema de integração via endpoints configurados no banco
4. Fluxo de push replica o ptm-regulation-service: find_patient → register/update → create_reminder
5. Push é idempotente (verifica se reminder já existe antes de criar)
6. Progresso visível em tempo real na tela do admin
7. Histórico de execuções persistido e consultável
8. Falha em um agendamento individual não interrompe o batch
9. Nenhuma referência hardcoded a sistema específico (tudo via DB)
10. Lint (ruff), testes (pytest + vitest), e build (next.js) passam sem erros
