# Enriquecimento CADSUS no Pipeline de Agendamentos

> **Status:** Em implementação
> **Data:** 2026-03-19
> **Depende de:** SCHEDULE_EXPORT.md, SCHEDULE_EXPORT_PIPELINE.md

## Resumo

Adicionar checkbox "Enriquecer com CADSUS" ao formulário de agendamentos. Quando marcado, o filtro de procedimento torna-se obrigatório. Após merge+dedup no pipeline, uma etapa "Enriquecimento" chama a API CADSUS para adicionar CPF, telefone, email, nome do pai, raça e CNS definitivo aos resultados filtrados.

## Fluxo

1. Pipeline per-operator: Login → Export → Results (com procedure_filter aplicado)
2. Merge + Dedup (consolidação dos resultados)
3. **Enriquecimento** (novo): POST batch de CNS únicos → CADSUS → merge no frontend
4. Final Count

## Backend

`POST /api/admin/sisreg/schedule-export/enrich` — recebe lista de CNS, retorna mapa de enriquecimento.

## Frontend

- Checkbox no ExportForm + procedureFilter obrigatório quando checked
- PipelineState: `enrichStatus`, `enrichedCount`
- DAG: node "Enriquecimento" entre Merge e Final (7 colunas)
- Hook: após MERGE, se enrich=true, chama endpoint e despacha ENRICH_SUCCESS
