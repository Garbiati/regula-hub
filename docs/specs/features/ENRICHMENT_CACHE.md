# Cache de Enriquecimento CADSUS

## Contexto

O endpoint `/enrich` consulta o CADSUS (e CadWeb como fallback) para obter CPF e telefone celular de pacientes a partir do CNS. Dois problemas identificados:

1. **Retry ineficiente:** Ao clicar "Tentar novamente" no pipeline, TODOS os CNS são re-consultados — incluindo os que já foram enriquecidos com sucesso. Com 2980 CNS e apenas 6 falhas, o retry faz ~500x mais chamadas que o necessário.

2. **Enriquecimento não persistido:** Os dados do CADSUS são mantidos apenas em memória no frontend. Quando dados cacheados do SisReg são carregados do banco, 100% dos CNS precisam ser re-enriquecidos, mesmo que o paciente tenha sido consultado recentemente.

## Solução

### Cache transparente no backend

Nova tabela `cadsus_enrichment_cache` indexada por `cns` (UNIQUE). O endpoint `/enrich` consulta o cache antes de chamar CADSUS:

1. Recebe `cns_list` (ex: 2980 CNS)
2. Query cache: entries com `enriched_at` nos últimos 30 dias
3. Separa: `cached` (já enriquecidos) + `pending` (a consultar)
4. Phase 1: CADSUS para `pending` apenas
5. Phase 2: CadWeb fallback para falhas do CADSUS
6. Upsert resultados novos no cache
7. Retorna `cached + novos` (transparente para o frontend)

### Retry inteligente no frontend

O hook `useExportPipeline` rastreia quais CNS falharam durante o enriquecimento. Ao clicar "Tentar novamente", apenas os CNS falhados são re-enviados ao `/enrich`.

## Schema

### Tabela: `cadsus_enrichment_cache`

| Coluna | Tipo | Restrições | Descrição |
|--------|------|-----------|-----------|
| `id` | UUID | PK | Chave primária |
| `cns` | VARCHAR(20) | UNIQUE, NOT NULL | Chave natural — CNS do paciente |
| `cpf` | VARCHAR(14) | NULL | CPF retornado pelo CADSUS/CadWeb |
| `phone` | VARCHAR(30) | NULL | Celular formatado |
| `email` | VARCHAR(200) | NULL | Email do paciente |
| `father_name` | VARCHAR(200) | NULL | Nome do pai |
| `race` | VARCHAR(50) | NULL | Raça/cor |
| `cns_definitivo` | VARCHAR(20) | NULL | CNS definitivo |
| `source` | VARCHAR(10) | NOT NULL | "CADSUS" ou "CADWEB" |
| `enriched_at` | TIMESTAMPTZ | NOT NULL | Quando foi enriquecido |
| `is_active` | BOOLEAN | NOT NULL, default true | Soft-delete |
| `created_at` | TIMESTAMPTZ | NOT NULL | Audit |
| `updated_at` | TIMESTAMPTZ | NULL | Audit |
| `created_by` | UUID | NULL | Audit |
| `updated_by` | UUID | NULL | Audit |

### Índices
- UNIQUE em `cns`
- `idx_enrich_cache_enriched_at` em `enriched_at`

## TTL

- **30 dias** — entries com `enriched_at` mais antigo que 30 dias são consideradas stale e re-consultadas
- Configurável via constante `ENRICHMENT_CACHE_TTL_DAYS = 30`

## Contrato API

### `POST /api/admin/sisreg/schedule-export/enrich` (modificado)

Request inalterado. Response ganha campo `from_cache`:

```json
{
  "results": { "111222333": { "cpf": "12345678901", "phone": "(92)99138-4577" } },
  "total": 2980,
  "found": 2974,
  "failed": 6,
  "fallback_found": 50,
  "from_cache": 2500
}
```

## Critérios de Aceite

1. **Retry parcial:** Botão "Tentar novamente" envia somente CNS que falharam
2. **Cache transparente:** CNS enriquecido nos últimos 30 dias não chama CADSUS
3. **Upsert:** Re-enriquecimento atualiza entry existente no cache
4. **TTL 30 dias:** Entries mais antigas são ignoradas e re-consultadas
5. **Retrocompatível:** Frontend existente funciona sem alterações (cache é transparente)
6. **PII em logs:** CNS nunca exposto em logs
