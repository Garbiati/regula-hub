# Visualização do Pipeline de Busca — Consulta SisReg

> **Status:** Em desenvolvimento
> **Data:** 2026-03-17
> **Escopo:** Frontend (admin) + Backend (novo endpoint)

## 1. Contexto

A tela `/sisreg/consulta` usa um spinner genérico durante a busca multi-operador. O usuário não tem visibilidade sobre quais operadores estão sendo consultados, quais falharam, ou quantos resultados cada um retornou.

## 2. Objetivo

Substituir o loading genérico por uma visualização animada em tempo real do pipeline de execução — estilo dbt lineage graph — mostrando cada etapa com retry por operador.

## 3. Pipeline Real do Backend

```
Operador 1 ──→ [Login SisReg] ──→ [Pesquisa] ──→ 15 itens ──┐
Operador 2 ──→ [Login SisReg] ──→ [Pesquisa] ──→ 20 itens ──┤──→ [Merge + Dedup] ──→ 32 únicos
Operador 3 ──→ [Login SisReg] ──→ [Pesquisa] ──→ ERRO ❌    ┘       (por código)
                                                  [Retry]
```

## 4. Decisões Arquiteturais

### 4.1 Frontend Orchestration (sem SSE)

O frontend faz N chamadas paralelas (1 por operador) ao novo endpoint `POST /api/admin/sisreg/search-operator`. Cada chamada completa independentemente, permitindo atualização em tempo real natural.

**Justificativa:** SSE adicionaria complexidade desproporcional para 1-5 operadores.

### 4.2 Modal Interativo com Confirmação

Pipeline aparece em um modal glassmorphism full-screen. Quando completo, o modal mostra:
- Resumo de sucesso/falha com detalhes por operador
- Operadores com falha listados com erro e botão de retry individual
- Botão "Ver Resultados" que o usuário deve clicar para fechar o modal e ver a tabela

**Justificativa:** Modal mantém o foco no pipeline, bloqueia interação com o formulário durante a busca, e exige confirmação antes de mostrar resultados. Isso garante que o usuário veja quais operadores falharam e tenha chance de retentá-los.

### 4.3 Animação CSS-only (High-Tech)

Sem framer-motion. Keyframes customizados em `globals.css`:
- `pipelinePulse` — glow respirante para nodes ativos
- `nodeSuccess` — pop + ring burst verde para sucesso
- `nodeShake` — shake + ring vermelho para erro
- `slideInScale` — entrada staggered dos cards
- `dotPulse` — partículas nos conectores ativos
- `mergeGlow` — glow pulsante no merge node
- `backdropIn` — blur-in do backdrop do modal

`prefers-reduced-motion` respeitado globalmente.

### 4.4 Layout Vertical no Modal

Layout vertical (top-to-bottom) dentro do modal, com conectores animados entre os nodes.

## 5. Especificação do Backend

### 5.1 Novo Modelo

```python
class OperatorSearchResponse(BaseModel):
    operator: str
    items: list[AppointmentListing]
    total: int
```

### 5.2 Novo Endpoint

- **Rota:** `POST /api/admin/sisreg/search-operator`
- **Rate limit:** `30/minute`
- **Corpo:** `SearchFilters` com exatamente 1 username
- **Resposta:** `OperatorSearchResponse`
- **Validação:** Rejeita se `len(usernames) != 1` com HTTP 422

### 5.3 Comportamento

1. Resolve credencial do username único
2. Executa busca via `SisregClient`
3. Retorna resultado com campo `operator` preenchido
4. Em caso de erro de login → HTTP 502
5. Credencial não encontrada → HTTP 404

## 6. Especificação do Frontend

### 6.1 Tipos (`types/pipeline.ts`)

- `PipelineNodeStatus`: `"idle" | "connecting" | "searching" | "success" | "error"`
- `OperatorPipelineState`: username, status, itemCount, error?
- `PipelineState`: operators[], mergeStatus, uniqueCount, isComplete

### 6.2 Hook (`hooks/use-pipeline-search.ts`)

Usa `useReducer` para orquestrar N buscas paralelas:

1. Recebe `SearchFilters` + `usernames[]`
2. Cada fetch: `idle` → `connecting` (800ms delay) → `searching` → `success`/`error`
3. Quando todos resolvem, roda dedup client-side por `code`
4. Expõe `retryOperator(username)` para retry individual
5. "connecting" simulado por 800ms (login real acontece na mesma request)

### 6.3 Componentes (`components/consultation/`)

| Componente | Responsabilidade |
|-----------|-----------------|
| `pipeline-visualization.tsx` | Container com layout horizontal/vertical |
| `pipeline-node.tsx` | Card individual por operador + merge node |
| `pipeline-connector.tsx` | Linha animada entre nodes |
| `pipeline-summary-bar.tsx` | Barra colapsada pós-busca |

### 6.4 Máquina de Estados

```
idle ──→ connecting ──→ searching ──→ success (N itens)
                                  └──→ error ──→ [retry] ──→ connecting
```

### 6.5 i18n Keys (pipeline.*)

~15 chaves nos 3 idiomas (pt-BR, en-US, es-AR).

## 7. Critérios de Aceitação

1. Pipeline sempre renderiza (mesmo com 1 operador)
2. Cada operador mostra estado visual distinto (idle/connecting/searching/success/error)
3. Retry funcional por operador com falha
4. Dedup client-side por `code` produz mesmos resultados que dedup server-side
5. Barra resumo mostra contagem total + operadores + tempo
6. `prefers-reduced-motion: reduce` desabilita animações
7. Layout vertical em mobile (< 768px)
8. Todos os testes passam (backend + frontend)

## 8. Testes

| Tipo | Arquivo | Escopo |
|------|---------|--------|
| Unit (backend) | `tests/unit/test_search_operator.py` | Endpoint, validação 1 username |
| Unit (reducer) | `admin/tests/unit/use-pipeline-search.test.ts` | Máquina de estados, dedup, retry |
| Unit (component) | `admin/tests/unit/pipeline-node.test.tsx` | Render por status, retry click |
| Integration | `admin/tests/integration/pipeline-search.test.tsx` | Fluxo completo com MSW |
