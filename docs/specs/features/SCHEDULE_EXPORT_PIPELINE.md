# Pipeline Modal para Exportação de Agendamentos

> **Status:** Em implementação
> **Autor:** Alessandro
> **Data:** 2026-03-19
> **Depende de:** [SCHEDULE_EXPORT.md](./SCHEDULE_EXPORT.md)

## 1. Contexto

A tela de agendamentos (`/sisreg/agendamentos`) executa a exportação multi-operador via um único POST que retorna todos os resultados de uma vez. Não há feedback visual sobre o progresso individual de cada operador — o usuário vê apenas um spinner até tudo terminar.

A tela de consulta (`/sisreg/consulta`) já possui um **Pipeline Modal** com visualização DAG que mostra o progresso em tempo real de cada operador (Login → Pesquisa → Resultados → Merge + Dedup). Essa experiência deve ser replicada na tela de agendamentos.

## 2. Solução

### 2.1 Backend — Endpoint single-operator

Novo endpoint no router de schedule-export:

```
POST /api/admin/sisreg/schedule-export/operator
```

**Request body:** `ScheduleExportRequest` com exatamente 1 username.

**Response:**
```json
{
  "operator": "username",
  "items": [ScheduleExportItemResponse...],
  "total": 42
}
```

Valida `len(usernames) == 1`, retorna 422 se não. Erros: 404 (credential not found), 502 (login/export failed).

Rate limit: `30/minute` (alinhado com `search-operator`).

### 2.2 Frontend — Hook `useExportPipeline`

Adaptação do `usePipelineSearch` para o fluxo de exportação:

- Chama `/api/admin/sisreg/schedule-export/operator` N vezes em paralelo (1 por operador)
- Rastreia status por operador: `idle → connecting → searching → success/error`
- Deduplicação por `solicitacao` (em vez de `code`)
- Merge final com contagem de únicos

### 2.3 Frontend — Página de agendamentos

- Botão "Buscar" abre o `PipelineModal` com visualização DAG
- Ao confirmar resultados, exibe na tabela
- Botões CSV/TXT continuam usando o endpoint bulk (sem pipeline)

### 2.4 Reutilização de componentes

Os componentes do pipeline (`PipelineModal`, `PipelineDag`, `PipelineCanvas`, `PipelineNode`, `PipelineEdge`) e os tipos (`PipelineState`, `OperatorPipelineState`) são **100% genéricos** — não possuem lógica específica de consulta. Serão importados diretamente de `components/consultation/`.

As labels dos steps ("Login SisReg", "Pesquisa", "Resultados") são semanticamente adequadas para exportação — o operador faz login e "pesquisa" os dados para exportar.

## 3. Arquivos

| Ação | Arquivo |
|------|---------|
| **Criar** | `admin/src/hooks/use-export-pipeline.ts` |
| **Modificar** | `admin/src/types/schedule-export.ts` (add `OperatorExportResponse`) |
| **Modificar** | `admin/src/app/sisreg/agendamentos/page.tsx` (add pipeline modal) |
| **Modificar** | `src/regulahub/api/controllers/admin/schedule_export_routes.py` (add single-operator endpoint) |
| **Modificar** | `src/regulahub/api/controllers/admin/schemas.py` (add response schema) |

## 4. Critérios de Aceite

- [ ] Endpoint single-operator funciona com exatamente 1 username
- [ ] Pipeline modal aparece ao clicar "Buscar" na tela de agendamentos
- [ ] Progresso individual por operador é exibido em tempo real
- [ ] Retry de operador com falha funciona
- [ ] Cancelamento aborta requisições pendentes
- [ ] Deduplicação por `solicitacao` no merge final
- [ ] Resultados confirmados aparecem na tabela
- [ ] Download CSV/TXT continua funcionando (endpoint bulk)
- [ ] Rate limiting no novo endpoint
- [ ] Auth obrigatório (`X-API-Key`)
