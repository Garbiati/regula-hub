# Spec: Migração do Admin Frontend — NiceGUI → Next.js + React + TypeScript

## 1. Contexto e Motivação

### 1.1 Situação Atual

O admin UI do RegulaHub é construído com **NiceGUI** (Python), rodando como processo separado na porta 8080. Embora funcional, apresenta limitações significativas:

| Limitação | Impacto |
|-----------|---------|
| Server-rendered Python UI | Cada interação do usuário faz round-trip ao servidor; sem reatividade client-side |
| Acoplamento Python ↔ UI | Lógica de apresentação misturada com acesso a banco e chamadas HTTP |
| NiceGUI é nicho | Pouca documentação, comunidade pequena, difícil para AI agents gerar código idiomático |
| Sem type safety no frontend | Erros de runtime em vez de compile-time; AI gera código mais frágil |
| CSS inline e global | 211 linhas de CSS injetado via `add_head_html()`; sem sistema de design consistente |
| Sem componentização real | Páginas são funções monolíticas; sem reuso estruturado de componentes |
| Sem testes de UI | Zero testes para as 11 páginas do admin |
| Sem SSR/SSG otimizado | NiceGUI renderiza tudo server-side via WebSocket, sem cache de página |

### 1.2 Objetivo

Migrar o frontend admin para uma stack moderna que maximize:

1. **Produtividade com AI agents** — tecnologia com mais dados de treinamento e padrões consolidados
2. **Type safety** — erros detectados em compile-time, não runtime
3. **Arquitetura limpa** — separação clara de responsabilidades, sem code smell
4. **Performance** — SSR, code splitting, caching automático
5. **Testabilidade** — testes unitários, de integração e E2E com ferramentas maduras
6. **DX (Developer Experience)** — hot reload, type inference, auto-complete, linting integrado

### 1.3 Decisão sobre o Backend

**O backend Python/FastAPI NÃO será migrado.** Justificativa:

- O backend está bem arquitetado (Strategy Pattern, Adapter Pattern, Repository Pattern)
- A lógica de scraping SisReg é complexa, testada e funcional
- Migrar para .NET/C# reescreveria ~4.000 linhas de código estável sem ganho funcional
- Python/FastAPI tem excelente suporte de AI agents (mesmo nível que TypeScript)
- O pipeline worker (APScheduler, rate limiter, managed session) é intrinsecamente assíncrono — Python async é ideal
- O custo de migração do backend seria desproporcional ao benefício

**Conclusão:** Migrar apenas o frontend. O backend FastAPI permanece inalterado, servindo como API para o novo frontend.

---

## 2. Análise de Tecnologias

### 2.1 Candidatos Avaliados

| Framework | Linguagem | Prós | Contras | Nota AI |
|-----------|-----------|------|---------|---------|
| **Next.js 15 + React 19** | TypeScript | Maior ecossistema React, SSR/SSG, App Router, Server Components, shadcn/ui | Mais boilerplate que Svelte | ⭐⭐⭐⭐⭐ |
| **SvelteKit 2** | TypeScript | Menos boilerplate, reatividade nativa, compilação | Ecossistema menor, menos dados de treinamento para AI | ⭐⭐⭐⭐ |
| **Nuxt 3 + Vue 3** | TypeScript | Composition API, auto-imports, Nuxt UI | Ecossistema mediano, Options vs Composition API confunde AI | ⭐⭐⭐ |
| **Angular 19** | TypeScript | Enterprise-grade, DI nativo, RxJS | Verboso, curva de aprendizado, AI gera código Angular mais pobre | ⭐⭐⭐ |
| **Blazor (WASM)** | C# | Expertise do usuário em .NET, type safety | Ecossistema web limitado, componentes fracos, bundle size alto | ⭐⭐ |
| **.NET MAUI Blazor Hybrid** | C# | Desktop + web | Imaturidade, poucos componentes, suporte AI fraco | ⭐ |

### 2.2 Análise Detalhada — Por que Next.js

#### Volume de Treinamento para AI Agents

Claude Opus tem treinamento massivo em React/Next.js/TypeScript. Isto resulta em:

- **Código idiomático** gerado na primeira tentativa (menos iterações de correção)
- **Padrões consolidados** (hooks, server components, data fetching) que o modelo conhece profundamente
- **Resolução de erros** mais rápida — o modelo reconhece stack traces e padrões de erro
- **Bibliotecas do ecossistema** — shadcn/ui, TanStack Query, Zustand, Zod são bem conhecidos

#### Comparativo Quantitativo

| Métrica | Next.js/React | SvelteKit | Nuxt/Vue | Blazor |
|---------|---------------|-----------|----------|--------|
| Stars GitHub (framework) | 132k (Next) + 235k (React) | 82k | 55k (Nuxt) + 48k (Vue) | N/A (.NET) |
| NPM weekly downloads | 7.5M (next) | 500K (svelte) | 600K (nuxt) | N/A |
| Componentes UI (shadcn) | 50+ prontos | Port não-oficial | Nuxt UI (30+) | MudBlazor (60+) |
| Stack Overflow questions | 450K+ (react) | 15K | 80K (vue) | 25K |
| Dados de treinamento AI | Máximo | Médio | Alto | Baixo-Médio |

### 2.3 Stack Escolhida

| Camada | Tecnologia | Versão | Justificativa |
|--------|------------|--------|---------------|
| **Framework** | Next.js (App Router) | 15.x | SSR, RSC, layouts, middleware, API routes |
| **UI Runtime** | React | 19.x | Server Components, Suspense, concurrent features |
| **Linguagem** | TypeScript | 5.x | Type safety, melhor DX, AI gera código mais correto |
| **Componentes** | shadcn/ui | latest | Copy-paste, customizável, Radix primitives, Tailwind |
| **Styling** | Tailwind CSS | 4.x | Utility-first, design tokens, purge automático |
| **Forms** | React Hook Form + Zod | latest | Validação type-safe, performance, zero re-renders |
| **Server State** | TanStack Query (React Query) | 5.x | Cache, refetch, optimistic updates, devtools |
| **Client State** | Zustand | 5.x | Minimal, type-safe, sem boilerplate |
| **Tabelas** | TanStack Table | 8.x | Headless, sorting, filtering, pagination, virtualização |
| **Charts** | Recharts | 2.x | Baseado em D3, declarativo, React-native |
| **Excel Export** | SheetJS (xlsx) | latest | Geração client-side, sem dependência do servidor |
| **i18n** | next-intl | latest | Type-safe, SSR-compatible, pluralização |
| **Data/Hora** | date-fns | latest | Tree-shakeable, imutável, locale pt-BR |
| **HTTP Client** | Fetch nativo + TanStack Query | built-in | Server Components usam fetch direto; client usa Query |
| **Testes** | Vitest + Testing Library + Playwright | latest | Unit + integration + E2E |
| **Lint** | ESLint + Prettier | latest | Config flat (ESLint 9), auto-fix |
| **Package Manager** | pnpm | 9.x | Rápido, disk-efficient, workspaces |

---

## 3. Inventário Completo de Features a Migrar

### 3.1 Páginas Funcionais (7)

#### P1: Dashboard (`/`)

| Feature | Detalhe |
|---------|---------|
| Status do Worker | enabled/disabled + running/stopped com pills coloridas |
| Modo de Integração | Indicador local/remote |
| KPI Cards (5) | Listed, Details, Transformed, Reminders, Errors com ícones e trends |
| Última Execução | Status, data, resumo de erros |
| Trigger Sync | Botão "Sync Today" + input de data customizada |
| Auto-refresh | Atualização periódica do status |

**API:** `GET /sync/status`, `POST /sync/trigger`

#### P2: Appointments (`/appointments`)

| Feature | Detalhe |
|---------|---------|
| Busca por data | Input de reference_date |
| Filtro por status | Dropdown com 12 status distintos |
| Tabela de resultados | 7 colunas: code, patient, procedure, date, time, status, department |
| Status pills | Coloridas por semântica (success/warning/danger/info) |
| Detail dialog | Modal com todos os campos do appointment ao clicar na linha |
| Export Excel | Download .xlsx com 15 colunas |

**Data Source:** Database direto (SQLAlchemy → `sisreg_appointments`)

#### P3: Raw Data (`/raw-data`)

| Feature | Detalhe |
|---------|---------|
| Busca por data | Input de reference_date |
| Tabela de resultados | 4 colunas: code, detail_fetched, failure_reason, created_at |
| JSON Viewer | Dialog com 2 tabs: Listing JSON e Detail JSON |
| Syntax highlight | JSON formatado com indentação |
| Failure tracking | Exibe failure_reason e failure_reason_details |

**Data Source:** Database direto (SQLAlchemy → `sisreg_raw_appointments`)

#### P4: Reference Data (`/reference`)

| Feature | Detalhe |
|---------|---------|
| Tab: Procedures | sisreg_code, procedure_name, speciality_name, speciality_id, work_scale_name, is_active |
| Tab: Departments | cnes, name, department_type, is_remote, is_active |
| Tab: Execution Mappings | requester_cnes, requester_name, executor_cnes, executor_name, municipality (limit 500) |
| Read-only | Sem edição — dados do .NET regulation-service |

**Data Source:** Database direto (raw SQL → tabelas .NET `sisreg_*`)

#### P5: Sync History (`/sync-history`)

| Feature | Detalhe |
|---------|---------|
| Busca por range de datas | dt_inicial + dt_final (default: últimos 7 dias) |
| Tabela de resultados | 8 colunas: date, status, started_at, listed, fetched, transformed, reminders, errors |
| Status pills | Coloridas por semântica |
| Detail dialog | Modal com: status, timestamps, duração, contadores detalhados, error_summary |

**Data Source:** Database direto (SQLAlchemy → `sisreg_sync_executions`)

#### P6: SisReg Console (`/sisreg/consulta`)

**Página mais complexa — substitui Postman para testes manuais.**

| Feature | Detalhe |
|---------|---------|
| Toggle: Search/Detail | Switch entre painel de busca e painel de detalhe |
| **Painel de Busca** | |
| Filtros (5 seções) | Period (tipo_periodo, datas, situacao), Procedure (3 campos), Patient/Request (3 campos), Units (2 campos), Pagination (3 campos) |
| Situação dinâmica | Opções de cmb_situacao mudam conforme tipo_periodo selecionado (S/A/E/P/C) |
| Calendar picker | Seletor de data com popup |
| Toggle: Table/JSON | Visualização em tabela ou JSON bruto |
| Tabela de resultados | 9 colunas: code, request_date, risk, patient, municipality, procedure, department, execution_date, status |
| Detail dialog | Seções expansíveis: requesting_unit, executing_unit, patient, solicitation, procedure |
| Export Excel | Download .xlsx dos resultados da busca |
| Badge com contagem | Exibe total de resultados |
| **Painel de Detalhe** | |
| Input de código | Busca por código de agendamento |
| Toggle: JSON/PDF | Formato de resposta |
| JSON display | Bloco de código com botão de copiar |
| PDF download | Download direto do PDF gerado pelo SisReg |
| Profile-aware | Muda endpoint conforme perfil ativo (videofonista vs solicitante) |

**API:** `GET /raw/videofonista/appointments`, `GET /raw/solicitante/appointments`, `GET /raw/{profile}/appointments/{code}`

#### P7: Profile Settings (`/sisreg/profile`)

| Feature | Detalhe |
|---------|---------|
| Profile selector | 2 cards clicáveis: Videofonista, Solicitante |
| Indicador visual | Card ativo com borda colorida e ícone |
| **Seção Videofonista** | |
| Filtro por estado | Dropdown extraído da lista de videofonistas |
| Lista com checkboxes | Username, estado |
| Select all / Deselect all | Botões de ação em massa |
| Validate credentials | POST para cada usuário, exibe ✓/✗ com tooltip de erro |
| Save | Persiste seleção no storage |
| **Seção Operadores (Solicitante)** | |
| Filtro por estado | Dropdown extraído da lista de operadores |
| Lista com checkboxes | Unit name, CNES, login |
| Validação de credenciais | Mesmo padrão da seção Videofonista |
| Save | Persiste seleção no storage |
| **Validações** | |
| Mesmo estado | Todos os selecionados devem ser do mesmo estado |
| Mesmo sistema | Todos os selecionados devem ser do mesmo sistema |

**API:** `GET /raw/operators`, `GET /raw/videofonistas`, `POST /raw/validate-credentials`

### 3.2 Páginas Placeholder (8)

4 sistemas futuros × 2 rotas cada:

| Sistema | Rotas | Status |
|---------|-------|--------|
| e-SUS Regulação | `/esus-regulacao/profile`, `/esus-regulacao/consulta` | Placeholder "Em breve" |
| SIGA Saúde | `/siga-saude/profile`, `/siga-saude/consulta` | Placeholder "Em breve" |
| Care Paraná | `/care-parana/profile`, `/care-parana/consulta` | Placeholder "Em breve" |
| SER (RJ) | `/ser-rj/profile`, `/ser-rj/consulta` | Placeholder "Em breve" |

### 3.3 Componentes Transversais

| Componente | Funcionalidade |
|------------|---------------|
| Sidebar | 5 itens fixos + 5 grupos expansíveis (SisReg + 4 futuros) |
| Header | Logo, título, relógio (hora local + UTC offset), seletor de idioma, chip de perfil |
| Status Pill | Badge colorida por status (12 variantes) |
| KPI Card | Ícone + valor + label + trend |
| i18n | 275+ chaves em 3 idiomas (pt-BR, en-US, es-AR) |
| Theme | 2 paletas de perfil (amber/videofonista, blue/solicitante) + 8 cores semânticas |
| Excel Export | 2 templates: appointments (15 cols) e raw appointments |
| Storage | 8 chaves persistentes (perfil, operadores, videofonistas, estado, caches) |

---

## 4. Arquitetura Proposta

### 4.1 Estrutura do Projeto

```text
admin/                              # Raiz do frontend (dentro de regula-hub)
├── .env.local                      # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_API_KEY
├── .eslintrc.js                    # ESLint flat config
├── .prettierrc                     # Prettier config
├── next.config.ts                  # Next.js config
├── tailwind.config.ts              # Tailwind + design tokens
├── tsconfig.json                   # TypeScript strict mode
├── vitest.config.ts                # Vitest config
├── playwright.config.ts            # Playwright E2E config
├── package.json
├── pnpm-lock.yaml
│
├── public/
│   ├── locales/                    # Arquivos de tradução
│   │   ├── pt-BR.json
│   │   ├── en-US.json
│   │   └── es-AR.json
│   └── favicon.ico
│
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── layout.tsx              # Root layout (providers, sidebar, header)
│   │   ├── page.tsx                # Dashboard (/)
│   │   ├── appointments/
│   │   │   └── page.tsx            # Appointments (/appointments)
│   │   ├── raw-data/
│   │   │   └── page.tsx            # Raw Data (/raw-data)
│   │   ├── reference/
│   │   │   └── page.tsx            # Reference Data (/reference)
│   │   ├── sync-history/
│   │   │   └── page.tsx            # Sync History (/sync-history)
│   │   ├── sisreg/
│   │   │   ├── consulta/
│   │   │   │   └── page.tsx        # SisReg Console
│   │   │   └── profile/
│   │   │       └── page.tsx        # Profile Settings
│   │   ├── esus-regulacao/
│   │   │   ├── consulta/page.tsx   # Placeholder
│   │   │   └── profile/page.tsx    # Placeholder
│   │   ├── siga-saude/
│   │   │   ├── consulta/page.tsx
│   │   │   └── profile/page.tsx
│   │   ├── care-parana/
│   │   │   ├── consulta/page.tsx
│   │   │   └── profile/page.tsx
│   │   └── ser-rj/
│   │       ├── consulta/page.tsx
│   │       └── profile/page.tsx
│   │
│   ├── components/                 # Componentes reutilizáveis
│   │   ├── ui/                     # shadcn/ui primitives (auto-gerado)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── tooltip.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── sheet.tsx           # Sidebar mobile
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── sidebar.tsx         # Sidebar com navegação
│   │   │   ├── header.tsx          # Header com clock, language, profile chip
│   │   │   ├── nav-item.tsx        # Item de navegação individual
│   │   │   └── nav-group.tsx       # Grupo expansível (sistemas futuros)
│   │   ├── shared/
│   │   │   ├── status-pill.tsx     # Badge de status com cor semântica
│   │   │   ├── kpi-card.tsx        # Card de métrica
│   │   │   ├── data-table.tsx      # Wrapper TanStack Table com sorting/filtering/pagination
│   │   │   ├── date-input.tsx      # Input de data com calendar picker
│   │   │   ├── date-range-input.tsx # Range de datas (sync history)
│   │   │   ├── json-viewer.tsx     # Visualizador JSON com syntax highlight
│   │   │   ├── excel-export-button.tsx # Botão de export genérico
│   │   │   ├── loading-skeleton.tsx # Skeleton screens para loading states
│   │   │   ├── error-boundary.tsx  # Error boundary com retry
│   │   │   └── placeholder-page.tsx # Template para sistemas futuros
│   │   ├── dashboard/
│   │   │   ├── worker-status.tsx
│   │   │   ├── sync-trigger.tsx
│   │   │   └── execution-summary.tsx
│   │   ├── appointments/
│   │   │   ├── appointment-filters.tsx
│   │   │   ├── appointment-table.tsx
│   │   │   └── appointment-detail-dialog.tsx
│   │   ├── raw-data/
│   │   │   ├── raw-data-table.tsx
│   │   │   └── json-detail-dialog.tsx
│   │   ├── reference/
│   │   │   ├── procedures-tab.tsx
│   │   │   ├── departments-tab.tsx
│   │   │   └── mappings-tab.tsx
│   │   ├── sync-history/
│   │   │   ├── sync-table.tsx
│   │   │   └── execution-detail-dialog.tsx
│   │   ├── sisreg-console/
│   │   │   ├── search-panel.tsx
│   │   │   ├── detail-panel.tsx
│   │   │   ├── filter-card.tsx
│   │   │   ├── results-table.tsx
│   │   │   ├── scheduling-detail.tsx
│   │   │   └── situacao-select.tsx  # Dropdown dinâmico
│   │   └── profile-settings/
│   │       ├── profile-selector.tsx
│   │       ├── videofonista-section.tsx
│   │       ├── operator-section.tsx
│   │       ├── credential-validator.tsx
│   │       └── user-list-with-checkboxes.tsx
│   │
│   ├── hooks/                      # Custom React hooks
│   │   ├── use-sync-status.ts      # GET /sync/status (polling)
│   │   ├── use-trigger-sync.ts     # POST /sync/trigger (mutation)
│   │   ├── use-appointments.ts     # GET /api/admin/appointments (query)
│   │   ├── use-raw-appointments.ts # GET /api/admin/raw-appointments
│   │   ├── use-reference-data.ts   # GET /api/admin/reference/{type}
│   │   ├── use-sync-history.ts     # GET /api/admin/sync-history
│   │   ├── use-sisreg-search.ts    # GET /raw/{profile}/appointments
│   │   ├── use-sisreg-detail.ts    # GET /raw/{profile}/appointments/{code}
│   │   ├── use-operators.ts        # GET /raw/operators + /raw/videofonistas
│   │   ├── use-validate-credentials.ts # POST /raw/validate-credentials
│   │   └── use-profile-store.ts    # Zustand store hook
│   │
│   ├── lib/                        # Utilitários e configuração
│   │   ├── api-client.ts           # Fetch wrapper com API key e base URL
│   │   ├── query-client.ts         # TanStack Query client config
│   │   ├── constants.ts            # Status list, system list, color maps
│   │   ├── utils.ts                # cn() helper, formatters
│   │   └── excel-export.ts         # Geração de Excel client-side
│   │
│   ├── stores/                     # Zustand stores
│   │   └── profile-store.ts        # Perfil ativo, operadores, videofonistas, estado
│   │
│   ├── types/                      # TypeScript types e interfaces
│   │   ├── appointment.ts          # Appointment, AppointmentDetail
│   │   ├── raw-appointment.ts      # RawAppointment
│   │   ├── sync-execution.ts       # SyncExecution, SyncStatus
│   │   ├── reference.ts            # Procedure, Department, ExecutionMapping
│   │   ├── sisreg.ts               # SisregAppointment, SchedulingDetail, FilterParams
│   │   ├── operator.ts             # Operator, Videofonista, CredentialValidation
│   │   └── api.ts                  # ApiResponse<T>, PaginatedResponse<T>, ErrorResponse
│   │
│   └── providers/                  # React context providers
│       ├── query-provider.tsx      # TanStack Query provider
│       ├── theme-provider.tsx      # Theme (profile palette) provider
│       └── i18n-provider.tsx       # Internacionalização provider
│
├── tests/
│   ├── unit/                       # Vitest unit tests
│   │   ├── components/             # Component tests com Testing Library
│   │   ├── hooks/                  # Hook tests
│   │   ├── stores/                 # Store tests
│   │   └── lib/                    # Utility tests
│   ├── integration/                # Integration tests
│   │   └── pages/                  # Page-level tests com MSW (API mocking)
│   └── e2e/                        # Playwright E2E
│       ├── dashboard.spec.ts
│       ├── appointments.spec.ts
│       └── sisreg-console.spec.ts
│
└── Dockerfile                      # Multi-stage: build + nginx/standalone
```

### 4.2 Diagrama de Dependências

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js App Router                        │
│                                                                  │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────────────┐ │
│  │  Pages    │──▶│  Components  │──▶│  shadcn/ui primitives   │ │
│  │  (app/)   │   │  (shared/)   │   │  (components/ui/)       │ │
│  └────┬─────┘   └──────┬───────┘   └─────────────────────────┘ │
│       │                │                                         │
│       ▼                ▼                                         │
│  ┌──────────┐   ┌──────────────┐                                │
│  │  Hooks   │──▶│  Stores      │                                │
│  │  (hooks/)│   │  (Zustand)   │                                │
│  └────┬─────┘   └──────────────┘                                │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────────────┐   ┌─────────────────────────────┐ │
│  │  API Client (lib/)       │──▶│  TanStack Query             │ │
│  │  fetch + headers + types │   │  cache, refetch, devtools   │ │
│  └──────────┬───────────────┘   └─────────────────────────────┘ │
│             │                                                    │
└─────────────┼────────────────────────────────────────────────────┘
              │ HTTP (fetch)
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (unchanged)                    │
│                                                                  │
│  /sync/status   /sync/trigger   /raw/{profile}/appointments     │
│  /raw/operators /raw/videofonistas /raw/validate-credentials    │
│                                                                  │
│  + NEW admin endpoints (see section 4.4)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Fluxo de Dados

```text
User Action → Component → Hook (useQuery/useMutation)
                              │
                              ▼
                         API Client (lib/api-client.ts)
                              │ fetch() with X-API-Key header
                              ▼
                         FastAPI Backend
                              │
                              ▼
                         PostgreSQL (or SisReg via HTTPX)
                              │
                              ▼
                         JSON Response
                              │
                              ▼
                         TanStack Query Cache
                              │
                              ▼
                         Component Re-render (type-safe data)
```

### 4.4 Novos Endpoints Necessários no Backend

O admin NiceGUI atual acessa o banco de dados diretamente (SQLAlchemy queries dentro das páginas). Na nova arquitetura, **todo acesso a dados passa pela API REST**. Novos endpoints necessários:

| Endpoint | Método | Descrição | Migra de |
|----------|--------|-----------|----------|
| `GET /api/admin/appointments` | GET | Lista appointments por data e status | Query direta em `appointments.py` |
| `GET /api/admin/appointments/{id}` | GET | Detalhe de um appointment | Query direta em `appointments.py` |
| `GET /api/admin/raw-appointments` | GET | Lista raw appointments por data | Query direta em `raw_data.py` |
| `GET /api/admin/raw-appointments/{id}` | GET | JSON de listing/detail | Query direta em `raw_data.py` |
| `GET /api/admin/reference/procedures` | GET | Lista procedures | Raw SQL em `reference.py` |
| `GET /api/admin/reference/departments` | GET | Lista departments | Raw SQL em `reference.py` |
| `GET /api/admin/reference/mappings` | GET | Lista execution mappings | Raw SQL em `reference.py` |
| `GET /api/admin/sync-history` | GET | Execuções por range de datas | Query direta em `sync_history.py` |
| `GET /api/admin/sync-history/{id}` | GET | Detalhe de uma execução | Query direta em `sync_history.py` |

**Nota:** Os endpoints `/sync/*` e `/raw/*` já existem e serão reutilizados diretamente.

---

## 5. Padrões de Desenvolvimento

### 5.1 Convenções de Código

| Aspecto | Convenção |
|---------|-----------|
| **Nomenclatura de arquivos** | `kebab-case.tsx` para componentes, `camelCase.ts` para utils/hooks |
| **Nomenclatura de componentes** | `PascalCase` (ex: `StatusPill`, `KpiCard`) |
| **Nomenclatura de hooks** | `use` prefix (ex: `useAppointments`, `useSyncStatus`) |
| **Nomenclatura de tipos** | `PascalCase`, sem prefixo I (ex: `Appointment`, não `IAppointment`) |
| **Exports** | Named exports apenas — sem default exports (facilita refactoring) |
| **Props** | Definidas com `interface` + `Props` suffix (ex: `interface StatusPillProps`) |
| **Barrel files** | Proibidos (`index.ts` que re-exportam) — imports diretos ao arquivo |
| **Idioma do código** | Inglês (variáveis, funções, tipos, comentários) — per CONSTITUTION.md §6 |

### 5.2 Padrões React

#### Server Components vs Client Components

```text
Server Components (default):
  - Pages que fazem data fetching direto
  - Layout components (sidebar, header)
  - Componentes sem interatividade

Client Components ("use client"):
  - Componentes com useState/useEffect
  - Componentes que usam hooks (useQuery, useForm)
  - Componentes com event handlers (onClick, onChange)
  - Componentes que acessam browser APIs (localStorage)
```

#### Padrão de Data Fetching

```typescript
// hooks/use-appointments.ts — tipo canônico
export function useAppointments(date: string, status?: string) {
  return useQuery({
    queryKey: ["appointments", date, status],
    queryFn: () => apiClient.get<Appointment[]>("/api/admin/appointments", {
      params: { date, status },
    }),
    enabled: !!date,
  });
}
```

#### Padrão de Componente

```typescript
// components/shared/status-pill.tsx — tipo canônico
interface StatusPillProps {
  status: AppointmentStatus;
  label?: string;
}

export function StatusPill({ status, label }: StatusPillProps) {
  const variant = STATUS_VARIANT_MAP[status];
  return <Badge variant={variant}>{label ?? status}</Badge>;
}
```

### 5.3 Padrões de Estado

```text
┌────────────────────────────────────────────────────────┐
│ Tipo de Estado         │ Solução                        │
├────────────────────────┼────────────────────────────────┤
│ Server state           │ TanStack Query (cache + fetch) │
│ (dados da API)         │                                │
├────────────────────────┼────────────────────────────────┤
│ Client state global    │ Zustand (profile, operators)   │
│ (preferências do user) │ + localStorage persistence     │
├────────────────────────┼────────────────────────────────┤
│ Form state             │ React Hook Form + Zod          │
│ (inputs temporários)   │                                │
├────────────────────────┼────────────────────────────────┤
│ UI state local         │ useState (modals, toggles)     │
│ (abrir/fechar dialog)  │                                │
└────────────────────────┴────────────────────────────────┘
```

### 5.4 Padrão de Internacionalização

```typescript
// public/locales/pt-BR.json (estrutura plana com namespace por prefixo)
{
  "nav.dashboard": "Painel",
  "nav.appointments": "Agendamentos",
  "common.search": "Pesquisar",
  "common.close": "Fechar",
  "dash.worker_status": "Status do Worker",
  "appt.regulation_code": "Código",
  "appt.patient_name": "Paciente",
  "status.new": "Novo",
  "status.pending_reminder": "Aguardando lembrete",
  ...
}

// Uso em componente:
const t = useTranslations();
return <span>{t("appt.regulation_code")}</span>;
```

**Migração das 275+ chaves:** As chaves existentes em `i18n.py` serão extraídas para 3 arquivos JSON (`pt-BR.json`, `en-US.json`, `es-AR.json`). A estrutura plana com prefixos de namespace é preferida por ser mais simples para AI agents e grep-friendly.

### 5.5 Padrão de Testes

| Tipo | Framework | O que testa | Cobertura alvo |
|------|-----------|-------------|----------------|
| **Unit** | Vitest + Testing Library | Componentes isolados, hooks, stores, utils | 80% |
| **Integration** | Vitest + MSW | Páginas completas com API mockada | Todas as 7 páginas |
| **E2E** | Playwright | Fluxos críticos contra app real | Dashboard + SisReg Console + Profile Settings |

```typescript
// tests/unit/components/status-pill.test.tsx — tipo canônico
describe("StatusPill", () => {
  it("renders success variant for sent_reminder status", () => {
    render(<StatusPill status="sent_reminder" />);
    expect(screen.getByText("sent_reminder")).toHaveAttribute(
      "data-variant",
      "success"
    );
  });
});
```

### 5.6 Design System

#### Tokens de Design (Tailwind)

```text
Colors (CSS variables — switch por perfil):
  --primary: amber-600 (videofonista) | blue-600 (solicitante)
  --secondary: amber-700 | blue-700
  --accent: amber-500 | blue-500

Semantic (fixas):
  --success: emerald-500 (#10B981)
  --danger: red-500 (#EF4444)
  --warning: amber-500 (#F59E0B)
  --info: blue-500 (#3B82F6)

Layout:
  Sidebar: 240px (desktop), Sheet (mobile)
  Header: 48px
  Content: fluid, px-6 py-8
  Cards: rounded-xl shadow-sm border
  Tables: striped rows, hover, sticky header
```

#### Responsividade

| Breakpoint | Layout |
|------------|--------|
| `< 768px` | Sidebar hidden (hamburger menu), cards stack vertical |
| `768px - 1024px` | Sidebar collapsed (ícones), 2-col grid |
| `> 1024px` | Sidebar expanded (240px), full layout |

---

## 6. Estratégia de Migração

### 6.1 Princípios

1. **Migração incremental** — cada fase entrega valor funcional
2. **Paridade antes de inovação** — replicar 100% das features antes de adicionar novas
3. **Backend first** — criar endpoints `/api/admin/*` antes do frontend que os consome
4. **Testes desde o início** — cada componente nasce com teste
5. **Feature flag** — ambos os admins (NiceGUI e Next.js) coexistem até a migração completa

### 6.2 Fases

#### Fase 0: Infraestrutura (1 entrega)

**Objetivo:** Projeto Next.js funcional com layout base.

- [ ] Inicializar projeto Next.js 15 com App Router + TypeScript strict
- [ ] Configurar Tailwind CSS 4 + design tokens (cores, breakpoints)
- [ ] Instalar e configurar shadcn/ui (componentes base)
- [ ] Configurar TanStack Query provider
- [ ] Configurar Zustand store (perfil, operadores)
- [ ] Configurar next-intl com os 3 arquivos de tradução (migrar de `i18n.py`)
- [ ] Implementar layout raiz: Sidebar + Header + Content area
- [ ] Implementar componentes de layout: `NavItem`, `NavGroup`, profile chip, clock, language selector
- [ ] Configurar `api-client.ts` (fetch wrapper com `X-API-Key`)
- [ ] Configurar Vitest + Testing Library + MSW
- [ ] Configurar ESLint + Prettier
- [ ] Dockerfile multi-stage (build + standalone/nginx)
- [ ] Adicionar serviço `admin-next` no `docker-compose.yml` (porta 3000)

**Critério de aceite:** Layout renderiza com sidebar navegável, header com clock/language/profile, e uma página em branco no content area. Testes do layout passam.

#### Fase 1: Páginas de Consulta Read-Only (4 entregas)

**Objetivo:** Páginas que apenas lêem dados do banco (sem interação com SisReg).

**1.1 — Endpoints Backend `/api/admin/*`**

- [ ] `GET /api/admin/appointments` — query params: `date`, `status` — retorna lista paginada
- [ ] `GET /api/admin/appointments/{id}` — retorna appointment completo
- [ ] `GET /api/admin/raw-appointments` — query params: `date` — retorna lista
- [ ] `GET /api/admin/raw-appointments/{id}` — retorna listing_json + detail_json
- [ ] `GET /api/admin/reference/procedures` — retorna todas as procedures ativas
- [ ] `GET /api/admin/reference/departments` — retorna todos os departments ativos
- [ ] `GET /api/admin/reference/mappings` — retorna execution mappings (limit 500)
- [ ] `GET /api/admin/sync-history` — query params: `from`, `to` — retorna execuções
- [ ] `GET /api/admin/sync-history/{id}` — retorna execução detalhada
- [ ] Testes para todos os endpoints (pytest + respx)

**1.2 — Componentes Shared**

- [ ] `StatusPill` — badge colorida por status
- [ ] `KpiCard` — card de métrica com ícone e trend
- [ ] `DataTable` — wrapper TanStack Table (sorting, filtering, pagination)
- [ ] `DateInput` — input de data com picker
- [ ] `DateRangeInput` — range de datas
- [ ] `JsonViewer` — syntax-highlighted JSON com copy
- [ ] `ExcelExportButton` — geração client-side com SheetJS
- [ ] `LoadingSkeleton` — skeleton screens
- [ ] `PlaceholderPage` — template para sistemas futuros
- [ ] Testes unitários para cada componente

**1.3 — Páginas Read-Only**

- [ ] Dashboard (`/`) — status do worker, KPIs, trigger sync
- [ ] Appointments (`/appointments`) — busca, tabela, detail dialog, export
- [ ] Raw Data (`/raw-data`) — busca, tabela, JSON viewer
- [ ] Reference Data (`/reference`) — 3 tabs (procedures, departments, mappings)
- [ ] Sync History (`/sync-history`) — range de datas, tabela, detail dialog
- [ ] Páginas placeholder (8 rotas) — usando `PlaceholderPage`
- [ ] Testes de integração para cada página (MSW)

**1.4 — Excel Export**

- [ ] `appointments_to_excel()` — 15 colunas, headers traduzidos
- [ ] `raw_appointments_to_excel()` — resultados do SisReg Console
- [ ] Testes para ambos os exports

#### Fase 2: SisReg Console (2 entregas)

**Objetivo:** Página mais complexa — substitui Postman.

**2.1 — Search Panel**

- [ ] `FilterCard` — 5 seções de filtros com validação Zod
- [ ] `SituacaoSelect` — dropdown dinâmico por tipo_periodo
- [ ] `ResultsTable` — 9 colunas com row click
- [ ] `SchedulingDetail` — seções expansíveis com field labels i18n
- [ ] Toggle Table/JSON
- [ ] Export Excel dos resultados
- [ ] Badge com contagem

**2.2 — Detail Panel**

- [ ] Input de código + fetch detail
- [ ] Toggle JSON/PDF
- [ ] JSON display com copy
- [ ] PDF download
- [ ] Profile-aware (endpoint muda conforme perfil)

#### Fase 3: Profile Settings (1 entrega)

**Objetivo:** Configuração de perfil e operadores.

- [ ] `ProfileSelector` — 2 cards (Videofonista/Solicitante)
- [ ] `VideofonistSection` — lista com checkboxes, filtro estado, validação
- [ ] `OperatorSection` — lista com checkboxes, filtro estado, validação
- [ ] `CredentialValidator` — POST /raw/validate-credentials, feedback visual
- [ ] Zustand store persistence (localStorage)
- [ ] Validação: mesmo estado + mesmo sistema
- [ ] Testes unitários e de integração

#### Fase 4: Polish e Cutover (1 entrega)

**Objetivo:** Paridade completa, testes E2E, remoção do NiceGUI.

- [ ] Testes E2E com Playwright (fluxos críticos)
- [ ] Auditoria de acessibilidade (Lighthouse)
- [ ] Verificação de responsividade (mobile/tablet)
- [ ] Verificação de i18n (3 idiomas em todas as páginas)
- [ ] Performance audit (Core Web Vitals)
- [ ] Atualizar `docker-compose.yml`: substituir serviço `admin` por `admin-next`
- [ ] Remover código NiceGUI (`src/regulahub/admin/`)
- [ ] Remover dependências NiceGUI do `pyproject.toml` (nicegui, openpyxl)
- [ ] Atualizar CLAUDE.md, TECH_SPEC.md, e diagramas de arquitetura
- [ ] Atualizar spec V1_LOCAL_PIPELINE.md

---

## 7. Docker Compose — Coexistência

Durante a migração, ambos os admins rodam simultaneamente:

```yaml
services:
  # ... postgres, api (unchanged) ...

  admin:          # NiceGUI (porta 8080) — será removido na Fase 4
    # ... existing config ...
    profiles: [admin]

  admin-next:     # Next.js (porta 3000)
    build:
      context: ./admin
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
      - NEXT_PUBLIC_API_KEY=dev-api-key-for-local
    depends_on:
      api:
        condition: service_healthy
    profiles: [admin-next]
```

---

## 8. Segurança e LGPD

| Requisito | Implementação |
|-----------|---------------|
| API Key | `X-API-Key` header em todas as requisições (via `api-client.ts`) |
| Sem PII em logs | Next.js server logs não incluem dados de pacientes |
| Sem PII em URL | Nenhum dado sensível em query parameters |
| CSP | Content-Security-Policy header via `next.config.ts` |
| CORS | API Backend configura `Access-Control-Allow-Origin` para o admin |
| Sanitização | Sem `dangerouslySetInnerHTML` — JSON renderizado via componente |
| Env vars | Segredos apenas em `.env.local` (gitignored), públicas com `NEXT_PUBLIC_` prefix |

---

## 9. Critérios de Aceitação Globais

- [ ] Todas as 7 páginas funcionais migradas com paridade de features
- [ ] Todas as 8 páginas placeholder renderizando
- [ ] i18n funcionando em 3 idiomas (pt-BR, en-US, es-AR) com 275+ chaves
- [ ] Theme switch por perfil (amber/videofonista, blue/solicitante)
- [ ] Export Excel funcionando em Appointments e SisReg Console
- [ ] Responsividade em desktop, tablet e mobile
- [ ] `pnpm test` → all pass (unit + integration)
- [ ] `pnpm test:e2e` → all pass (Playwright)
- [ ] `pnpm lint` → clean
- [ ] `pnpm build` → sem erros TypeScript
- [ ] Lighthouse Performance ≥ 90, Accessibility ≥ 95
- [ ] Docker `admin-next` inicia e conecta ao backend
- [ ] NiceGUI removido completamente após cutover
- [ ] CLAUDE.md e specs atualizados

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Novos endpoints `/api/admin/*` introduzem bugs | Média | Alto | Testes pytest com cobertura ≥ 80% |
| SisReg Console é muito complexo para migrar | Baixa | Alto | Componentes granulares, testes por seção |
| Incompatibilidade de tipos entre Python e TypeScript | Média | Médio | Tipos TypeScript espelham Pydantic schemas |
| Latência de rede (frontend → API → DB) vs acesso direto ao DB | Baixa | Baixo | TanStack Query caching, staleTime configurável |
| Perda de storage do NiceGUI na migração | Baixa | Médio | Zustand + localStorage usa as mesmas chaves |
| Next.js 15 breaking changes durante o dev | Baixa | Médio | Fixar versão no package.json |
