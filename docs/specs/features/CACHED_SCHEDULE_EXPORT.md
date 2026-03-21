# Cache Persistente de Agendamentos (Schedule Export)

## Contexto

O SisReg III bloqueia acesso entre 8h e 15h (horário de Brasília). Para que a equipe possa consultar agendamentos durante o horário restrito, implementamos um cache persistente no banco de dados PostgreSQL.

O operador controla a persistência via checkbox opcional na interface de exportação de agendamentos. Quando ativado:
1. Resultados previamente cacheados são carregados do banco de dados
2. Pipeline SisReg normal executa em paralelo (multi-operador)
3. Resultados são mesclados com deduplicação por `solicitacao` (SisReg tem prioridade)
4. Dados novos/atualizados são persistidos no banco via upsert

## Identificador Único

`solicitacao` — código de solicitação do SisReg. Usado como chave natural para deduplicação e upsert.

## Regras de Negócio

### Persistência Controlada
- Cache é **opt-in** — checkbox OFF por padrão
- Dados protegidos pelas mesmas regras de acesso da API (X-API-Key)
- PII nunca exposto em logs (regra existente mantida)
- Autorizado pela atualização da CONSTITUTION.md §1 e BUSINESS_RULES.md

### Fluxo por Estado do Checkbox

| Estado | Comportamento |
|--------|--------------|
| **OFF** (padrão) | Busca somente no SisReg — comportamento atual inalterado |
| **ON + Pesquisa** | Query DB → Pipeline SisReg → Merge (dedup por solicitacao, SisReg prioridade) → Upsert DB → Retorna mergeado |

### Deduplicação
- SisReg tem prioridade: rows do SisReg são inseridos primeiro no array de merge
- `deduplicateBySolicitacao()` mantém o primeiro visto (= SisReg)
- Cache preenche gaps de operadores offline ou dados antigos

## Schema do Banco

### Tabela: `sisreg_cached_exports`

| Coluna | Tipo | Restrições | Descrição |
|--------|------|-----------|-----------|
| `id` | UUID | PK, default uuid4 | Chave primária |
| `solicitacao` | VARCHAR(30) | UNIQUE, NOT NULL | Chave natural — código de solicitação |
| `data_agendamento` | VARCHAR(10) | NOT NULL | Formato original dd/MM/yyyy |
| `data_agendamento_iso` | DATE | NULL, INDEXED | Para range queries indexadas |
| `descricao_procedimento` | VARCHAR(300) | NOT NULL | Para filtro ILIKE |
| `row_data` | JSONB | NOT NULL | ScheduleExportRow completo |
| `is_active` | BOOLEAN | NOT NULL, default true | Soft-delete |
| `created_at` | TIMESTAMPTZ | NOT NULL, default now() | Audit |
| `updated_at` | TIMESTAMPTZ | NULL | Audit |
| `created_by` | UUID | NULL | Audit |
| `updated_by` | UUID | NULL | Audit |

### Índices
- `idx_cached_exp_date_iso` em `data_agendamento_iso`
- `idx_cached_exp_procedure` em `descricao_procedimento`
- UNIQUE em `solicitacao`

## Contrato API

### POST `/api/admin/sisreg/schedule-export/cached`

Query cache do banco de dados.

**Request:**
```json
{
  "date_from": "01/03/2026",
  "date_to": "31/03/2026",
  "procedure_filter": "TELECONSULTA"
}
```

**Response:**
```json
{
  "items": [{ "solicitacao": "...", "dataAgendamento": "...", ... }],
  "total": 150
}
```

### POST `/api/admin/sisreg/schedule-export/persist`

Upsert rows no cache.

**Request:**
```json
{
  "items": [{ "solicitacao": "...", "dataAgendamento": "...", ... }]
}
```

**Response:**
```json
{
  "persisted": 150
}
```

## UX

### Checkbox no Formulário
- Localizado na seção "Cache Persistente" abaixo de "Enriquecimento"
- Label: "Banco de dados"
- Descrição: "Salvar resultados no banco e carregar cache offline"
- Estado padrão: OFF

### Pipeline Modal
- Quando cache carregado, mostra contagem no summary: "({count} do cache)"
- Quando persistido, mostra status "Salvo no banco de dados"

## Critérios de Aceite

1. **Checkbox OFF**: Comportamento idêntico ao atual — nenhuma query ao banco
2. **Checkbox ON + SisReg disponível**: Carrega cache → busca SisReg → merge → persist → retorna tudo
3. **Checkbox ON + SisReg indisponível**: Retorna dados do cache (mesmo com operadores falhando)
4. **Deduplicação**: Rows do SisReg sobrescrevem cache quando `solicitacao` coincide
5. **Upsert**: Rows existentes no cache são atualizados (`row_data`, `updated_at`)
6. **Soft-delete**: `is_active=false` exclui do cache sem deletar fisicamente
7. **PII em logs**: Nenhum dado de paciente aparece em logs
8. **Paginação**: Endpoints de cache respeitam contratos existentes
