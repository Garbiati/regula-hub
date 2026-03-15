# Plano de Implementação — Migração Admin Frontend (NiceGUI → Next.js)

> **Spec de referência:** [ADMIN_FRONTEND_MIGRATION.md](ADMIN_FRONTEND_MIGRATION.md)
>
> Stack: Next.js 15 + React 19 + TypeScript + shadcn/ui + TanStack Query + Zustand
>
> Cada passo é numerado como `Fase.Entrega.Grupo.Passo` (ex: 0.1.1.1).
> Passos marcados com ✅ estão concluídos.

---

## Fase 0 — Infraestrutura

### 0.1 Scaffolding do Projeto Next.js

#### 0.1.1 Inicialização

- **0.1.1.1** Criar diretório `admin/` na raiz do repositório
- **0.1.1.2** Executar `pnpm create next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"` dentro de `admin/`
- **0.1.1.3** Remover boilerplate gerado: `src/app/page.tsx` (conteúdo default), `public/` assets desnecessários, `src/app/globals.css` (conteúdo default)
- **0.1.1.4** Configurar `tsconfig.json`: `strict: true`, `noUncheckedIndexedAccess: true`, `forceConsistentCasingInFileNames: true`

#### 0.1.2 Dependências

- **0.1.2.1** Instalar dependências de UI: `pnpm add @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react`
- **0.1.2.2** Instalar TanStack: `pnpm add @tanstack/react-query @tanstack/react-table`
- **0.1.2.3** Instalar state management: `pnpm add zustand`
- **0.1.2.4** Instalar forms: `pnpm add react-hook-form @hookform/resolvers zod`
- **0.1.2.5** Instalar i18n: `pnpm add next-intl`
- **0.1.2.6** Instalar utils: `pnpm add date-fns xlsx recharts`
- **0.1.2.7** Instalar dev dependencies: `pnpm add -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitejs/plugin-react msw playwright @playwright/test prettier eslint-config-prettier`
- **0.1.2.8** Verificar `package.json` — todas as deps instaladas sem conflitos

#### 0.1.3 Configuração de Lint e Formatação

- **0.1.3.1** Criar `admin/.prettierrc` — `semi: true`, `singleQuote: false`, `tabWidth: 2`, `trailingComma: "all"`, `printWidth: 100`
- **0.1.3.2** Atualizar `admin/eslint.config.mjs` — estender `next/core-web-vitals`, `next/typescript`, `prettier`; regras: `no-unused-vars: warn`, `@typescript-eslint/no-explicit-any: error`
- **0.1.3.3** Adicionar scripts ao `package.json`: `"lint": "next lint"`, `"format": "prettier --write src/"`, `"format:check": "prettier --check src/"`
- **0.1.3.4** Verificar: `pnpm lint` → clean, `pnpm format:check` → clean

#### 0.1.4 Configuração de Testes

- **0.1.4.1** Criar `admin/vitest.config.ts` — environment: `jsdom`, globals: true, setupFiles: `./tests/setup.ts`, include: `["tests/**/*.test.{ts,tsx}"]`, coverage: provider `v8`
- **0.1.4.2** Criar `admin/tests/setup.ts` — importar `@testing-library/jest-dom/vitest`
- **0.1.4.3** Criar `admin/playwright.config.ts` — baseURL: `http://localhost:3000`, webServer: `pnpm dev`, projects: chromium
- **0.1.4.4** Adicionar scripts ao `package.json`: `"test": "vitest run"`, `"test:watch": "vitest"`, `"test:coverage": "vitest run --coverage"`, `"test:e2e": "playwright test"`
- **0.1.4.5** Criar `admin/tests/unit/.gitkeep`, `admin/tests/integration/.gitkeep`, `admin/tests/e2e/.gitkeep`
- **0.1.4.6** Verificar: `pnpm test` → 0 tests, sem erros

#### 0.1.5 Variáveis de Ambiente

- **0.1.5.1** Criar `admin/.env.local` — `NEXT_PUBLIC_API_URL=http://localhost:8000`, `NEXT_PUBLIC_API_KEY=dev-api-key-for-local`
- **0.1.5.2** Criar `admin/.env.example` — mesmas variáveis com valores placeholder
- **0.1.5.3** Adicionar `admin/.env.local` ao `admin/.gitignore`
- **0.1.5.4** Criar `admin/src/lib/env.ts` — validação de env vars com Zod: `NEXT_PUBLIC_API_URL` (string url), `NEXT_PUBLIC_API_KEY` (string min 1)

---

### 0.2 Design System (Tailwind + shadcn/ui)

#### 0.2.1 Tailwind Design Tokens

- **0.2.1.1** Editar `admin/tailwind.config.ts` — adicionar cores customizadas usando CSS variables:
  - `--primary`, `--secondary`, `--accent` (switch por perfil)
  - `--success: #10B981`, `--danger: #EF4444`, `--warning: #F59E0B`, `--info: #3B82F6`
  - `--surface: #FFFFFF`, `--surface-alt: #F9FAFB`, `--border: #E5E7EB`
  - `--text-primary: #111827`, `--text-secondary: #6B7280`, `--text-muted: #9CA3AF`
- **0.2.1.2** Definir breakpoints customizados: `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`
- **0.2.1.3** Editar `admin/src/app/globals.css` — definir CSS variables `:root` com valores default (videofonista palette: `--primary: 37.7 92.1% 50.2%` amber-600)

#### 0.2.2 shadcn/ui Setup

- **0.2.2.1** Executar `pnpm dlx shadcn@latest init` — style: default, baseColor: neutral, cssVariables: yes
- **0.2.2.2** Instalar componentes base: `pnpm dlx shadcn@latest add button card dialog input select table tabs badge tooltip separator sheet dropdown-menu collapsible popover calendar checkbox label scroll-area skeleton toggle`
- **0.2.2.3** Verificar que `admin/src/components/ui/` contém todos os componentes instalados
- **0.2.2.4** Criar `admin/src/lib/utils.ts` — função `cn()` (merge tailwind classes): `export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }`

#### 0.2.3 Constantes de Design

- **0.2.3.1** Criar `admin/src/lib/constants.ts` — exportar:
  - `PROFILE_PALETTES`: `{ videofonista: { primary: "#D97706", secondary: "#B45309", accent: "#F59E0B", chipBg: "#FEF3C7", chipText: "#92400E" }, solicitante: { primary: "#2563EB", secondary: "#1D4ED8", accent: "#3B82F6", chipBg: "#DBEAFE", chipText: "#1E40AF" } }`
  - `STATUS_VARIANT_MAP`: `{ new: "info", pending_reminder: "warning", sent_reminder: "success", detail_not_found: "destructive", procedure_not_found: "destructive", department_not_found: "destructive", date_in_past: "secondary", register_patient_error: "destructive", send_reminder_error: "destructive", unknown_error: "destructive", doctor_not_found: "warning", running: "info", completed: "success", failed: "destructive" }`
  - `SIDEBAR_ITEMS`: array com 5 itens `{ labelKey, path, icon }` — dashboard(/), appointments(/appointments), raw-data(/raw-data), reference(/reference), sync-history(/sync-history)
  - `SIDEBAR_GROUPS`: array com 5 grupos `{ labelKey, icon, link, children }` — SisReg, e-SUS, SIGA, Care Paraná, SER
  - `APPOINTMENT_STATUSES`: array dos 11 valores de AppointmentStatus
  - `SYNC_STATUSES`: array dos 3 valores de SyncStatus

---

### 0.3 Providers e Configuração

#### 0.3.1 API Client

- **0.3.1.1** Criar `admin/src/lib/api-client.ts`:
  - Classe `ApiClient` com `baseUrl` e `apiKey` lidos de env vars
  - Método `async get<T>(path, params?)` — fetch GET com `X-API-Key` header, parse JSON, type-safe return
  - Método `async post<T>(path, body?)` — fetch POST com `X-API-Key` header
  - Método `async getBlob(path, params?)` — para download de PDF
  - Tratamento de erros: throw `ApiError` customizado com status, message, detail
  - Exportar instância singleton: `export const apiClient = new ApiClient()`
- **0.3.1.2** Criar `admin/src/lib/api-error.ts` — classe `ApiError extends Error` com `status: number`, `detail?: string`
- **0.3.1.3** Teste: `admin/tests/unit/lib/api-client.test.ts` — testar GET/POST com fetch mockado, testar error handling

#### 0.3.2 TanStack Query Provider

- **0.3.2.1** Criar `admin/src/lib/query-client.ts` — configurar `QueryClient` com defaults: `staleTime: 30_000` (30s), `retry: 1`, `refetchOnWindowFocus: false`
- **0.3.2.2** Criar `admin/src/providers/query-provider.tsx` — `"use client"`, `QueryClientProvider` wrapper com React state para QueryClient (evitar re-criação em SSR)
- **0.3.2.3** Teste: `admin/tests/unit/providers/query-provider.test.tsx` — renderiza children sem erro

#### 0.3.3 Theme Provider

- **0.3.3.1** Criar `admin/src/providers/theme-provider.tsx` — `"use client"`, lê perfil do Zustand store, injeta CSS variables (--primary, --secondary, --accent) no `<html>` element via useEffect
- **0.3.3.2** Teste: `admin/tests/unit/providers/theme-provider.test.tsx` — verifica que CSS vars mudam ao trocar perfil

#### 0.3.4 i18n Provider

- **0.3.4.1** Criar `admin/src/providers/i18n-provider.tsx` — `"use client"`, `NextIntlClientProvider` wrapper, carrega mensagens do locale ativo
- **0.3.4.2** Criar `admin/src/i18n/request.ts` — configuração server-side do next-intl: `getRequestConfig`, default locale `pt-BR`
- **0.3.4.3** Criar `admin/src/middleware.ts` — middleware Next.js para internacionalização (detectar/persistir locale)

---

### 0.4 Layout (Sidebar + Header)

#### 0.4.1 Root Layout

- **0.4.1.1** Editar `admin/src/app/layout.tsx` — importar fontes (Inter), wrappear children com `QueryProvider`, `ThemeProvider`, `I18nProvider`
- **0.4.1.2** Estrutura HTML: `<html>` → `<body>` → `<div className="flex h-screen">` → `<Sidebar />` + `<div className="flex-1 flex flex-col">` → `<Header />` + `<main>{children}</main>`

#### 0.4.2 Sidebar

- **0.4.2.1** Criar `admin/src/components/layout/sidebar.tsx` — `"use client"`:
  - Container: `w-60 bg-white border-r h-full flex flex-col`
  - Logo/título no topo: ícone + "RegulaHub"
  - Seção "Navegação" com label muted
  - Iterar `SIDEBAR_ITEMS` → renderizar `NavItem` para cada
  - Separador
  - Seção "Sistemas" com label muted
  - Iterar `SIDEBAR_GROUPS` → renderizar `NavGroup` para cada
  - Mobile: usar `Sheet` (shadcn) com trigger hamburger
- **0.4.2.2** Criar `admin/src/components/layout/nav-item.tsx` — `"use client"`:
  - Props: `{ labelKey: string; path: string; icon: string; }`
  - Usa `usePathname()` para detectar item ativo
  - Ativo: fundo com cor primária do perfil (CSS var), texto branco, rounded-lg
  - Inativo: hover com bg-gray-100
  - Texto traduzido via `useTranslations()`
  - Ícone: Lucide icon mapeado por nome
- **0.4.2.3** Criar `admin/src/components/layout/nav-group.tsx` — `"use client"`:
  - Props: `{ labelKey: string; icon: string; link: string; children: { labelKey: string; path: string; icon: string; }[] }`
  - Usa `Collapsible` (shadcn) para expandir/colapsar
  - Click no header navega para `link` (profile page)
  - Children renderizados como sub-items indentados
  - Grupo ativo se `pathname` começa com prefixo do grupo
- **0.4.2.4** Teste: `admin/tests/unit/components/layout/sidebar.test.tsx` — renderiza 5 nav items + 5 groups, item ativo tem classe correta
- **0.4.2.5** Teste: `admin/tests/unit/components/layout/nav-item.test.tsx` — ativo vs inativo, click navega
- **0.4.2.6** Teste: `admin/tests/unit/components/layout/nav-group.test.tsx` — expand/collapse, children visíveis

#### 0.4.3 Header

- **0.4.3.1** Criar `admin/src/components/layout/header.tsx` — `"use client"`:
  - Container: `h-12 bg-white border-b flex items-center px-4 gap-4`
  - Mobile: hamburger button (sheet trigger para sidebar)
  - Logo + "RegulaHub" (sm:hidden no mobile, visível desktop)
  - Spacer (`flex-1`)
  - Clock component inline (hora local + UTC offset, atualizado a cada segundo via setInterval)
  - Language selector: `Select` (shadcn) com 3 opções (pt-BR, en-US, es-AR), onChange muda locale
  - Profile chip: badge colorida com nome do perfil ativo + estado selecionado, cores do `PROFILE_PALETTES`
- **0.4.3.2** Teste: `admin/tests/unit/components/layout/header.test.tsx` — clock renderiza, language selector tem 3 opções, profile chip mostra perfil do store
- **0.4.3.3** Verificar: `pnpm dev` → app renderiza com sidebar + header + content area vazio

---

### 0.5 Internacionalização (i18n)

#### 0.5.1 Extração das Chaves

- **0.5.1.1** Ler `src/regulahub/admin/i18n.py` — extrair todas as 403 chaves do dicionário `TRANSLATIONS`
- **0.5.1.2** Criar `admin/public/locales/pt-BR.json` — todas as chaves com valores em pt-BR, estrutura plana `{ "nav.dashboard": "Painel", ... }`
- **0.5.1.3** Criar `admin/public/locales/en-US.json` — todas as chaves com valores em en-US
- **0.5.1.4** Criar `admin/public/locales/es-AR.json` — todas as chaves com valores em es-AR
- **0.5.1.5** Verificar contagem: cada arquivo deve ter exatamente 403 chaves

#### 0.5.2 Configuração next-intl

- **0.5.2.1** Editar `admin/next.config.ts` — adicionar plugin `createNextIntlPlugin()` wrapping a config
- **0.5.2.2** Criar `admin/src/i18n/config.ts` — exportar `locales = ["pt-BR", "en-US", "es-AR"]`, `defaultLocale = "pt-BR"`
- **0.5.2.3** Atualizar `admin/src/i18n/request.ts` — carregar JSON do locale via `import()` dinâmico
- **0.5.2.4** Teste: `admin/tests/unit/i18n/translations.test.ts` — verificar que os 3 JSONs têm as mesmas chaves, nenhuma chave faltando

---

### 0.6 Docker

#### 0.6.1 Dockerfile do Admin Next.js

- **0.6.1.1** Criar `admin/Dockerfile` — multi-stage build:
  - **Stage 1 (deps):** `node:22-alpine`, `corepack enable`, `pnpm install --frozen-lockfile`
  - **Stage 2 (build):** copy source, `pnpm build` (Next.js standalone output)
  - **Stage 3 (runtime):** `node:22-alpine`, copy `.next/standalone` + `.next/static` + `public/`, `EXPOSE 3000`, `CMD ["node", "server.js"]`
- **0.6.1.2** Criar `admin/.dockerignore` — `node_modules`, `.next`, `tests/`, `.env.local`

#### 0.6.2 Docker Compose

- **0.6.2.1** Editar `docker-compose.yml` — adicionar serviço `admin-next`:
  - build: context `./admin`, dockerfile `Dockerfile`
  - ports: `3000:3000`
  - environment: `NEXT_PUBLIC_API_URL=http://api:8000`, `NEXT_PUBLIC_API_KEY=dev-api-key-for-local`
  - depends_on: `api` (condition: service_healthy)
  - profiles: `[admin-next]`
  - volumes (dev): `./admin/src:/app/src` (hot reload)
- **0.6.2.2** Verificar: `docker compose --profile admin-next up -d admin-next` → container healthy, `http://localhost:3000` renderiza layout

---

## Fase 1 — Páginas Read-Only

### 1.1 Backend — Novos Endpoints `/api/admin/*`

#### 1.1.1 Controller Admin — Estrutura

- **1.1.1.1** Criar diretório `src/regulahub/api/controllers/admin/`
- **1.1.1.2** Criar `src/regulahub/api/controllers/admin/__init__.py` — vazio
- **1.1.1.3** Criar `src/regulahub/api/controllers/admin/schemas.py` — schemas Pydantic para respostas:
  - `AdminAppointmentItem(BaseModel)` — todos os campos de `Appointment` model (regulation_code, confirmation_key, reference_date, appointment_date, appointment_time, patient_first_name, patient_last_name, procedure_name, speciality_name, status, dept_execute_name, dept_execute_cnes, doctor_execute_name, integration_error_message, etc.) — 25+ campos
  - `AdminAppointmentListResponse(BaseModel)` — `items: list[AdminAppointmentItem]`, `total: int`
  - `AdminRawAppointmentItem(BaseModel)` — id, regulation_code, reference_date, listing_json, detail_json, detail_fetched_at, failure_reason, failure_reason_details, created_at
  - `AdminRawAppointmentListResponse(BaseModel)` — `items: list[AdminRawAppointmentItem]`, `total: int`
  - `AdminProcedureItem(BaseModel)` — sisreg_code, procedure_name, speciality_name, speciality_id, work_scale_name, is_active
  - `AdminDepartmentItem(BaseModel)` — cnes, name (department_name), department_type, is_remote, is_active
  - `AdminMappingItem(BaseModel)` — requester_cnes, requester_name, executor_cnes, executor_name, municipality, is_active
  - `AdminSyncExecutionItem(BaseModel)` — herdar campos de `SyncExecutionSummary` existente + duration_seconds calculado
  - `AdminSyncExecutionListResponse(BaseModel)` — `items: list[AdminSyncExecutionItem]`, `total: int`

- **1.1.1.4** Criar `src/regulahub/api/controllers/admin/routes.py` — `APIRouter(prefix="/api/admin", tags=["admin"])`:

  **Endpoint: GET /api/admin/appointments**
  - Query params: `date: str` (YYYY-MM-DD, required), `status: str | None` (optional)
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: reusar `AppointmentRepository.get_by_date()` ou `.get_by_status()` conforme params
  - Response: `AdminAppointmentListResponse`

  **Endpoint: GET /api/admin/appointments/{appointment_id}**
  - Path param: `appointment_id: UUID`
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: query `select(Appointment).where(Appointment.id == appointment_id)`
  - Response: `AdminAppointmentItem` ou 404

  **Endpoint: GET /api/admin/raw-appointments**
  - Query params: `date: str` (YYYY-MM-DD, required)
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: query `select(RawAppointment).where(RawAppointment.reference_date == date).order_by(RawAppointment.regulation_code)`
  - Response: `AdminRawAppointmentListResponse`

  **Endpoint: GET /api/admin/raw-appointments/{raw_id}**
  - Path param: `raw_id: UUID`
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: query by ID
  - Response: `AdminRawAppointmentItem` ou 404

  **Endpoint: GET /api/admin/reference/procedures**
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: raw SQL `SELECT sisreg_code, procedure_name, speciality_name, speciality_id, work_scale_name, is_active FROM sisreg_procedures ORDER BY procedure_name` (reusar padrão de `admin/pages/reference.py`)
  - Response: `list[AdminProcedureItem]`

  **Endpoint: GET /api/admin/reference/departments**
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: raw SQL `SELECT department_cnes_code as cnes, department_name as name, department_type, is_remote, is_active FROM sisreg_departments ORDER BY department_name`
  - Response: `list[AdminDepartmentItem]`

  **Endpoint: GET /api/admin/reference/mappings**
  - Query params: `limit: int = 500`
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: raw SQL `SELECT requester_cnes, requester_name, executor_cnes, executor_name, municipality, is_active FROM sisreg_department_execution_mapping WHERE is_active = true ORDER BY municipality LIMIT :limit`
  - Response: `list[AdminMappingItem]`

  **Endpoint: GET /api/admin/sync-history**
  - Query params: `from_date: str` (YYYY-MM-DD), `to_date: str` (YYYY-MM-DD)
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: query `select(SyncExecution).where(SyncExecution.started_at.between(from_date, to_date + 1 day)).order_by(SyncExecution.started_at.desc())`
  - Response: `AdminSyncExecutionListResponse`

  **Endpoint: GET /api/admin/sync-history/{execution_id}**
  - Path param: `execution_id: UUID`
  - Dependency: `verify_api_key`, `get_session`
  - Lógica: reusar `SyncExecutionRepository.get_by_id()`
  - Response: `AdminSyncExecutionItem` ou 404

- **1.1.1.5** Registrar router no `src/regulahub/main.py` — `app.include_router(admin_router)`

#### 1.1.2 CORS para Admin Next.js

- **1.1.2.1** Atualizar `CORS_ORIGINS` no `.env` — adicionar `http://localhost:3000` à lista
- **1.1.2.2** Verificar que `main.py` já faz split por vírgula em `cors_origins`

#### 1.1.3 Testes Backend

- **1.1.3.1** Criar `tests/unit/test_admin_api.py`:
  - Fixture: SQLite async session, seed com 3 appointments, 2 raw_appointments, 1 sync_execution
  - Test GET /api/admin/appointments?date=2026-03-10 → 200, total=3
  - Test GET /api/admin/appointments?date=2026-03-10&status=new → filtra corretamente
  - Test GET /api/admin/appointments/{id} → 200, retorna appointment completo
  - Test GET /api/admin/appointments/{uuid-inexistente} → 404
  - Test GET /api/admin/raw-appointments?date=2026-03-10 → 200, total=2
  - Test GET /api/admin/raw-appointments/{id} → 200, inclui listing_json e detail_json
  - Test GET /api/admin/reference/procedures → 200, lista com procedures
  - Test GET /api/admin/reference/departments → 200
  - Test GET /api/admin/reference/mappings → 200, respects limit
  - Test GET /api/admin/sync-history?from_date=...&to_date=... → 200
  - Test GET /api/admin/sync-history/{id} → 200
  - Test todos os endpoints sem API key → 401
- **1.1.3.2** Verificar: `poetry run pytest tests/unit/test_admin_api.py -v` → all pass
- **1.1.3.3** Verificar: `poetry run ruff check src/regulahub/api/controllers/admin/` → clean

---

### 1.2 Types TypeScript

#### 1.2.1 Domain Types

- **1.2.1.1** Criar `admin/src/types/appointment.ts`:
  - `interface Appointment` — espelhar TODOS os campos de `AdminAppointmentItem` do backend: `id: string`, `regulationCode: string`, `confirmationKey: string`, `referenceDate: string`, `appointmentDate: string`, `appointmentTime: string`, `patientFirstName: string`, `patientLastName: string`, `patientBirthDate: string`, `patientCpf: string`, `patientCns: string`, `patientMotherName: string`, `bestPhone: string`, `saudeDigitalPatientId: string | null`, `isNewAccount: boolean`, `procedureName: string`, `specialityId: number`, `specialityName: string`, `workScaleId: string`, `workScaleName: string`, `deptSolicitationName: string`, `deptSolicitationCnes: string`, `deptExecuteName: string`, `deptExecuteCnes: string`, `deptExecuteAddress: string`, `isRemote: boolean`, `saudeDigitalGroupId: string | null`, `doctorExecuteName: string`, `doctorExecuteId: string | null`, `status: AppointmentStatus`, `integrationErrorMessage: string | null`, `saudeDigitalAppointmentId: string | null`, `createdAt: string`, `updatedAt: string | null`
  - `type AppointmentStatus` — union literal dos 11 valores: `"new" | "pending_reminder" | "sent_reminder" | "detail_not_found" | "procedure_not_found" | "department_not_found" | "date_in_past" | "register_patient_error" | "send_reminder_error" | "unknown_error" | "doctor_not_found"`
  - `interface AppointmentListResponse` — `{ items: Appointment[]; total: number }`

- **1.2.1.2** Criar `admin/src/types/raw-appointment.ts`:
  - `interface RawAppointment` — `id: string`, `syncExecutionId: string`, `regulationCode: string`, `referenceDate: string`, `listingJson: Record<string, unknown>`, `detailJson: Record<string, unknown> | null`, `detailFetchedAt: string | null`, `failureReason: FailureReason | null`, `failureReasonDetails: string | null`, `createdAt: string`
  - `type FailureReason` — `"timeout" | "parse_error" | "session_expired" | "not_found" | "http_error" | "unknown"`
  - `interface RawAppointmentListResponse` — `{ items: RawAppointment[]; total: number }`

- **1.2.1.3** Criar `admin/src/types/sync-execution.ts`:
  - `interface SyncExecution` — `id: string`, `referenceDate: string`, `startedAt: string`, `finishedAt: string | null`, `status: SyncStatus`, `totalListed: number`, `totalDetailsFetched: number`, `totalTransformed: number`, `totalIntegrated: number`, `totalRemindersSent: number`, `totalErrors: number`, `errorSummary: string | null`, `durationSeconds: number | null`
  - `type SyncStatus` — `"running" | "completed" | "failed"`
  - `interface SyncExecutionListResponse` — `{ items: SyncExecution[]; total: number }`
  - `interface WorkerStatus` — `{ enabled: boolean; isRunning: boolean; lastExecution: SyncExecution | null }`
  - `interface SyncTriggerResponse` — `{ executionId: string; message: string }`

- **1.2.1.4** Criar `admin/src/types/reference.ts`:
  - `interface Procedure` — `sisregCode: string`, `procedureName: string`, `specialityName: string`, `specialityId: number`, `workScaleName: string`, `isActive: boolean`
  - `interface Department` — `cnes: string`, `name: string`, `departmentType: string`, `isRemote: boolean`, `isActive: boolean`
  - `interface ExecutionMapping` — `requesterCnes: string`, `requesterName: string`, `executorCnes: string`, `executorName: string`, `municipality: string`, `isActive: boolean`

- **1.2.1.5** Criar `admin/src/types/sisreg.ts`:
  - `interface SisregAppointment` — `code: string`, `requestDate: string`, `risk: string`, `patient: string`, `phone: string`, `municipality: string`, `age: string`, `procedure: string`, `cid: string`, `departmentSolicitation: string`, `departmentExecute: string`, `executionDate: string`, `statusSisreg: string`
  - `interface SisregListResponse` — `{ appointments: SisregAppointment[]; total: number; currentPage: number; totalPages: number }`
  - `interface SchedulingDetail` — `{ confirmationKey: string; justification: string; requestingUnit: Record<string, string>; executingUnit: Record<string, string>; patient: Record<string, string>; solicitation: Record<string, string>; procedure: Record<string, string> }`
  - `interface SisregFilterParams` — todos os 15 query params do endpoint /raw/videofonista/appointments

- **1.2.1.6** Criar `admin/src/types/operator.ts`:
  - `interface Operator` — `unitCnes: string`, `unitName: string`, `username: string`, `system: string`, `state: string`, `stateName: string`
  - `interface Videofonista` — `username: string`, `system: string`, `state: string`, `stateName: string`
  - `interface CredentialValidation` — `username: string`, `valid: boolean`, `error: string | null`

- **1.2.1.7** Criar `admin/src/types/api.ts`:
  - `interface ApiError` — `status: number`, `message: string`, `detail?: string`

---

### 1.3 API Client Hooks

#### 1.3.1 Hooks de Query (TanStack)

- **1.3.1.1** Criar `admin/src/hooks/use-sync-status.ts` — `useQuery` com queryKey `["sync", "status"]`, `queryFn: () => apiClient.get<WorkerStatus>("/sync/status")`, `refetchInterval: 10_000` (polling 10s)
- **1.3.1.2** Criar `admin/src/hooks/use-trigger-sync.ts` — `useMutation` com `mutationFn: (date?: string) => apiClient.post<SyncTriggerResponse>("/sync/trigger", { date })`, `onSuccess: invalidate ["sync", "status"]`
- **1.3.1.3** Criar `admin/src/hooks/use-appointments.ts` — `useQuery` com queryKey `["admin", "appointments", date, status]`, `queryFn: () => apiClient.get<AppointmentListResponse>("/api/admin/appointments", { date, status })`, `enabled: !!date`
- **1.3.1.4** Criar `admin/src/hooks/use-appointment-detail.ts` — `useQuery` com queryKey `["admin", "appointments", id]`, `enabled: !!id`
- **1.3.1.5** Criar `admin/src/hooks/use-raw-appointments.ts` — `useQuery` com queryKey `["admin", "raw-appointments", date]`, `enabled: !!date`
- **1.3.1.6** Criar `admin/src/hooks/use-raw-appointment-detail.ts` — `useQuery` com queryKey `["admin", "raw-appointments", id]`, `enabled: !!id`
- **1.3.1.7** Criar `admin/src/hooks/use-reference-data.ts` — 3 hooks: `useProcedures()`, `useDepartments()`, `useMappings(limit?)`, cada um com `staleTime: 5 * 60 * 1000` (5min, dados mudam raramente)
- **1.3.1.8** Criar `admin/src/hooks/use-sync-history.ts` — `useQuery` com queryKey `["admin", "sync-history", fromDate, toDate]`, `enabled: !!fromDate && !!toDate`
- **1.3.1.9** Criar `admin/src/hooks/use-sync-execution-detail.ts` — `useQuery` com queryKey `["admin", "sync-history", id]`, `enabled: !!id`

#### 1.3.2 Testes de Hooks

- **1.3.2.1** Criar `admin/tests/unit/hooks/use-appointments.test.ts` — mock fetch, verificar queryKey, verificar enabled=false quando date é vazio
- **1.3.2.2** Criar `admin/tests/unit/hooks/use-sync-status.test.ts` — verificar polling interval, verificar data shape

---

### 1.4 Componentes Shared

#### 1.4.1 StatusPill

- **1.4.1.1** Criar `admin/src/components/shared/status-pill.tsx` — `"use client"`:
  - Props: `{ status: string; label?: string }`
  - Mapeia status → variant via `STATUS_VARIANT_MAP`
  - Renderiza `Badge` (shadcn) com variant e texto
  - Fallback para "secondary" se status desconhecido
- **1.4.1.2** Teste: `admin/tests/unit/components/shared/status-pill.test.tsx` — 4 cases: new→info, sent_reminder→success, failed→destructive, unknown→secondary

#### 1.4.2 KpiCard

- **1.4.2.1** Criar `admin/src/components/shared/kpi-card.tsx` — `"use client"`:
  - Props: `{ value: string | number; label: string; icon: string; trend?: string; trendPositive?: boolean }`
  - Card (shadcn) com: ícone em circle bg, valor em text-2xl font-bold, label em text-sm text-muted, trend em text-xs com cor (green/red)
- **1.4.2.2** Teste: `admin/tests/unit/components/shared/kpi-card.test.tsx` — renderiza value, label, icon; trend positivo verde, negativo vermelho

#### 1.4.3 DataTable

- **1.4.3.1** Criar `admin/src/components/shared/data-table.tsx` — `"use client"`:
  - Props genéricas: `{ columns: ColumnDef<T>[]; data: T[]; onRowClick?: (row: T) => void; isLoading?: boolean; emptyMessage?: string }`
  - Usa TanStack Table: `useReactTable` com `getCoreRowModel`, `getSortedRowModel`, `getPaginationRowModel`
  - Header com sorting indicators (chevron up/down)
  - Body com striped rows (`even:bg-gray-50`), hover effect
  - Pagination footer: prev/next buttons, page info "Página X de Y"
  - Loading state: `Skeleton` rows
  - Empty state: mensagem centralizada
  - Row click handler com cursor-pointer
- **1.4.3.2** Teste: `admin/tests/unit/components/shared/data-table.test.tsx` — renderiza colunas, sorting funciona, pagination funciona, onRowClick chamado

#### 1.4.4 DateInput

- **1.4.4.1** Criar `admin/src/components/shared/date-input.tsx` — `"use client"`:
  - Props: `{ value: string; onChange: (value: string) => void; label?: string; placeholder?: string }`
  - Input (shadcn) type="date" com formatação YYYY-MM-DD
  - Opcionalmente: Popover com Calendar (shadcn) para picker visual
- **1.4.4.2** Teste: `admin/tests/unit/components/shared/date-input.test.tsx` — onChange chamado com formato correto

#### 1.4.5 DateRangeInput

- **1.4.5.1** Criar `admin/src/components/shared/date-range-input.tsx` — `"use client"`:
  - Props: `{ fromDate: string; toDate: string; onFromChange: (v: string) => void; onToChange: (v: string) => void }`
  - Dois `DateInput` lado a lado com labels "De" e "Até"
- **1.4.5.2** Teste: `admin/tests/unit/components/shared/date-range-input.test.tsx`

#### 1.4.6 JsonViewer

- **1.4.6.1** Criar `admin/src/components/shared/json-viewer.tsx` — `"use client"`:
  - Props: `{ data: unknown; title?: string }`
  - Renderiza `JSON.stringify(data, null, 2)` em bloco `<pre><code>` com font-mono
  - Botão "Copiar" que faz `navigator.clipboard.writeText()`
  - Syntax highlight via classes CSS (chaves azul, strings verde, números laranja)
- **1.4.6.2** Teste: `admin/tests/unit/components/shared/json-viewer.test.tsx` — renderiza JSON formatado, botão copiar existe

#### 1.4.7 ExcelExportButton

- **1.4.7.1** Criar `admin/src/components/shared/excel-export-button.tsx` — `"use client"`:
  - Props: `{ data: Record<string, unknown>[]; columns: { key: string; header: string }[]; filename: string; disabled?: boolean }`
  - onClick: gera workbook com SheetJS (`XLSX.utils.json_to_sheet`), download via `XLSX.writeFile`
  - Botão com ícone download + texto traduzido
- **1.4.7.2** Teste: `admin/tests/unit/components/shared/excel-export-button.test.tsx` — click gera blob (mock XLSX)

#### 1.4.8 LoadingSkeleton

- **1.4.8.1** Criar `admin/src/components/shared/loading-skeleton.tsx`:
  - Props: `{ rows?: number; columns?: number }`
  - Renderiza grid de `Skeleton` (shadcn) retangulares simulando tabela
- **1.4.8.2** Teste: `admin/tests/unit/components/shared/loading-skeleton.test.tsx`

#### 1.4.9 PlaceholderPage

- **1.4.9.1** Criar `admin/src/components/shared/placeholder-page.tsx`:
  - Props: `{ systemName: string; icon: string }`
  - Centralizado: ícone grande, título do sistema, mensagem "Em breve" traduzida (`t("placeholder.coming_soon")`)
- **1.4.9.2** Teste: `admin/tests/unit/components/shared/placeholder-page.test.tsx`

#### 1.4.10 ErrorBoundary

- **1.4.10.1** Criar `admin/src/components/shared/error-boundary.tsx` — `"use client"`:
  - Class component (ErrorBoundary precisa de getDerivedStateFromError)
  - Fallback: card com ícone de erro, mensagem, botão "Tentar novamente" (reset)
- **1.4.10.2** Teste: `admin/tests/unit/components/shared/error-boundary.test.tsx` — captura erro, mostra fallback, reset funciona

---

### 1.5 Página Dashboard

#### 1.5.1 Componentes do Dashboard

- **1.5.1.1** Criar `admin/src/components/dashboard/worker-status.tsx` — `"use client"`:
  - Usa `useSyncStatus()` hook
  - 2 badges: Worker (enabled/disabled), Status (running/stopped)
  - Integration mode indicator (local/remote)
  - Skeleton durante loading

- **1.5.1.2** Criar `admin/src/components/dashboard/execution-summary.tsx` — `"use client"`:
  - Usa dados de `lastExecution` do `useSyncStatus()`
  - KPI cards (5): total_listed, total_details_fetched, total_transformed, total_reminders_sent, total_errors
  - Se lastExecution null: mensagem "Nenhuma execução registrada"
  - Error summary expandível se houver erros

- **1.5.1.3** Criar `admin/src/components/dashboard/sync-trigger.tsx` — `"use client"`:
  - Usa `useTriggerSync()` mutation hook
  - Botão "Sync Today" — onClick: `trigger()` sem date (usa hoje)
  - Input de data + botão "Sync Custom Date" — onClick: `trigger(customDate)`
  - Loading spinner durante mutation
  - Toast de sucesso/erro via sonner ou shadcn toast

#### 1.5.2 Página

- **1.5.2.1** Editar `admin/src/app/page.tsx`:
  - Título "Dashboard" com `useTranslations()`
  - Layout: `WorkerStatus` no topo, `ExecutionSummary` com KPIs, `SyncTrigger` na parte inferior
  - Tudo em cards separados

- **1.5.2.2** Teste: `admin/tests/integration/pages/dashboard.test.tsx` — MSW mock para /sync/status, verifica KPIs renderizados, trigger funciona

---

### 1.6 Página Appointments

#### 1.6.1 Componentes

- **1.6.1.1** Criar `admin/src/components/appointments/appointment-filters.tsx` — `"use client"`:
  - Props: `{ onSearch: (date: string, status?: string) => void }`
  - DateInput para reference_date
  - Select para status (dropdown com 12 opções + "Todos")
  - Botão "Pesquisar"

- **1.6.1.2** Criar `admin/src/components/appointments/appointment-table.tsx` — `"use client"`:
  - Props: `{ appointments: Appointment[]; onRowClick: (appt: Appointment) => void; isLoading: boolean }`
  - DataTable com 7 colunas: regulation_code, patient_first_name, procedure_name, appointment_date, appointment_time, status (StatusPill), dept_execute_name
  - Column definitions com headers traduzidos via i18n

- **1.6.1.3** Criar `admin/src/components/appointments/appointment-detail-dialog.tsx` — `"use client"`:
  - Props: `{ appointment: Appointment | null; open: boolean; onClose: () => void }`
  - Dialog (shadcn) com título = regulation_code
  - Seções: Patient Info, Procedure Info, Department Info, Integration Info
  - Cada seção: grid 2 colunas com label + value
  - Status pill grande no topo

#### 1.6.2 Excel Export Config

- **1.6.2.1** Criar `admin/src/lib/excel-export.ts`:
  - `APPOINTMENT_EXPORT_COLUMNS` — array de 15 `{ key, headerKey }` espelhando `export.py`: regulation_code, confirmation_key, reference_date, appointment_date, appointment_time, patient_first_name, patient_last_name, patient_cns, procedure_name, speciality_name, status, dept_execute_name, dept_execute_cnes, doctor_execute_name, integration_error_message
  - `RAW_APPOINTMENT_EXPORT_COLUMNS` — array de 13 `{ key, headerKey }`: code, request_date, risk, patient, phone, municipality, age, procedure, cid, department_solicitation, department_execute, execution_date, status_sisreg
  - Função `exportToExcel(data, columns, filename, t)` — genérica, traduz headers, gera xlsx

#### 1.6.3 Página

- **1.6.3.1** Criar `admin/src/app/appointments/page.tsx` — `"use client"`:
  - State: `date`, `status`, `selectedAppointment`
  - Usa `useAppointments(date, status)` hook
  - Layout: `AppointmentFilters` + `AppointmentTable` + `AppointmentDetailDialog`
  - ExcelExportButton com APPOINTMENT_EXPORT_COLUMNS
- **1.6.3.2** Teste: `admin/tests/integration/pages/appointments.test.tsx` — MSW mock, busca por data, filtro por status, export Excel

---

### 1.7 Página Raw Data

#### 1.7.1 Componentes

- **1.7.1.1** Criar `admin/src/components/raw-data/raw-data-table.tsx` — DataTable com 4 colunas: regulation_code, detail_fetched (boolean → Yes/No badge), failure_reason, created_at
- **1.7.1.2** Criar `admin/src/components/raw-data/json-detail-dialog.tsx` — Dialog com Tabs (Listing JSON / Detail JSON), cada tab com JsonViewer; se detail_json null: mensagem "Detalhes não disponíveis" + failure_reason + failure_reason_details

#### 1.7.2 Página

- **1.7.2.1** Criar `admin/src/app/raw-data/page.tsx` — DateInput + search button, RawDataTable, JsonDetailDialog ao clicar
- **1.7.2.2** Teste: `admin/tests/integration/pages/raw-data.test.tsx`

---

### 1.8 Página Reference Data

#### 1.8.1 Componentes

- **1.8.1.1** Criar `admin/src/components/reference/procedures-tab.tsx` — DataTable com 6 colunas (sisreg_code, procedure_name, speciality_name, speciality_id, work_scale_name, is_active como badge)
- **1.8.1.2** Criar `admin/src/components/reference/departments-tab.tsx` — DataTable com 5 colunas (cnes, name, department_type, is_remote badge, is_active badge)
- **1.8.1.3** Criar `admin/src/components/reference/mappings-tab.tsx` — DataTable com 5 colunas (requester_cnes, requester_name, executor_cnes, executor_name, municipality)

#### 1.8.2 Página

- **1.8.2.1** Criar `admin/src/app/reference/page.tsx` — Tabs (shadcn) com 3 abas: Procedures, Departments, Execution Mappings; cada tab usa respectivo componente e hook (useProcedures, useDepartments, useMappings)
- **1.8.2.2** Teste: `admin/tests/integration/pages/reference.test.tsx`

---

### 1.9 Página Sync History

#### 1.9.1 Componentes

- **1.9.1.1** Criar `admin/src/components/sync-history/sync-table.tsx` — DataTable com 8 colunas: reference_date, status (StatusPill), started_at, total_listed, total_details_fetched, total_transformed, total_reminders_sent, total_errors
- **1.9.1.2** Criar `admin/src/components/sync-history/execution-detail-dialog.tsx` — Dialog com: status pill, started_at, finished_at, duration (calculado), todos os contadores em grid, error_summary em card vermelho se presente

#### 1.9.2 Página

- **1.9.2.1** Criar `admin/src/app/sync-history/page.tsx` — DateRangeInput (default: últimos 7 dias), SyncTable, ExecutionDetailDialog
- **1.9.2.2** Teste: `admin/tests/integration/pages/sync-history.test.tsx`

---

### 1.10 Placeholder Pages

- **1.10.1.1** Criar `admin/src/app/esus-regulacao/profile/page.tsx` — `<PlaceholderPage systemName="e-SUS Regulação" icon="swap_horiz" />`
- **1.10.1.2** Criar `admin/src/app/esus-regulacao/consulta/page.tsx` — idem
- **1.10.1.3** Criar `admin/src/app/siga-saude/profile/page.tsx` — `<PlaceholderPage systemName="SIGA Saúde" icon="local_hospital" />`
- **1.10.1.4** Criar `admin/src/app/siga-saude/consulta/page.tsx` — idem
- **1.10.1.5** Criar `admin/src/app/care-parana/profile/page.tsx` — `<PlaceholderPage systemName="Care Paraná" icon="favorite" />`
- **1.10.1.6** Criar `admin/src/app/care-parana/consulta/page.tsx` — idem
- **1.10.1.7** Criar `admin/src/app/ser-rj/profile/page.tsx` — `<PlaceholderPage systemName="SER (RJ)" icon="account_balance" />`
- **1.10.1.8** Criar `admin/src/app/ser-rj/consulta/page.tsx` — idem

---

## Fase 2 — SisReg Console

### 2.1 Search Panel

#### 2.1.1 Hooks SisReg

- **2.1.1.1** Criar `admin/src/hooks/use-sisreg-search.ts` — `useQuery` com queryKey dinâmico baseado em todos os filterParams, endpoint varia por perfil (videofonista vs solicitante), inclui `operators` param para solicitante
- **2.1.1.2** Criar `admin/src/hooks/use-sisreg-detail.ts` — `useQuery` com queryKey `["sisreg", "detail", profile, code, format]`, endpoint varia por perfil, suporta format=json e format=pdf (blob)

#### 2.1.2 Componentes de Filtro

- **2.1.2.1** Criar `admin/src/components/sisreg-console/situacao-select.tsx` — `"use client"`:
  - Props: `{ tipoPeriodo: string; value: string; onChange: (v: string) => void }`
  - Mapa de opções dinâmico: `S` → códigos 1-12 (exceto 8), `A/E` → códigos 9,10,12, `P` → código 7, `C` → código 11
  - Cada código tem label traduzido via i18n (`api.sit_1`, `api.sit_2`, ...)
  - Select (shadcn) com opções filtradas por tipoPeriodo

- **2.1.2.2** Criar `admin/src/components/sisreg-console/filter-card.tsx` — `"use client"`:
  - Props: `{ filters: SisregFilterParams; onChange: (filters: SisregFilterParams) => void; onSearch: () => void }`
  - 5 seções com Card + left border (profile color):
    1. **Período:** tipo_periodo (Select: S/A/E/P/C), dt_inicial (DateInput), dt_final (DateInput), cmb_situacao (SituacaoSelect)
    2. **Procedimento:** co_pa_interno (Input), co_proc_unificado (Input), ds_procedimento (Input)
    3. **Paciente/Solicitação:** co_solicitacao (Input), cns_paciente (Input), no_usuario (Input)
    4. **Unidades:** cnes_solicitante (Input), cnes_executante (Input)
    5. **Paginação:** qtd_itens_pag (Select: 0/10/20/50/100), ordenacao (Select: 1/2/3/4), pagina (Input number)
  - Botão "Pesquisar" no final
  - Validação Zod: dt_inicial e dt_final obrigatórios, formato dd/MM/yyyy

#### 2.1.3 Componentes de Resultado

- **2.1.3.1** Criar `admin/src/components/sisreg-console/results-table.tsx` — DataTable com 9 colunas traduzidas: code, request_date, risk, patient, municipality, procedure, department_execute, execution_date, status_sisreg; row click abre detalhe
- **2.1.3.2** Criar `admin/src/components/sisreg-console/scheduling-detail.tsx` — `"use client"`:
  - Props: `{ detail: SchedulingDetail }`
  - Campos top-level: confirmation_key, justification
  - 5 seções expansíveis (Collapsible): requesting_unit, executing_unit, patient, solicitation, procedure
  - Cada seção: grid 2 colunas com field labels traduzidos via FIELD_LABEL_MAP (migrado do i18n)
  - Left border colorida por perfil

#### 2.1.4 Search Panel Completo

- **2.1.4.1** Criar `admin/src/components/sisreg-console/search-panel.tsx` — `"use client"`:
  - State: filterParams, results, selectedDetail, viewMode (table/json)
  - FilterCard + Button "Pesquisar"
  - Badge com total de resultados
  - Toggle Table/JSON (shadcn Toggle)
  - Se table: ResultsTable + row click → fetch detail → Dialog com SchedulingDetail
  - Se json: JsonViewer com dados brutos
  - ExcelExportButton com RAW_APPOINTMENT_EXPORT_COLUMNS
- **2.1.4.2** Teste: `admin/tests/integration/pages/sisreg-console-search.test.tsx` — MSW mock, filtros funcionam, toggle funciona, detail dialog abre

### 2.2 Detail Panel

- **2.2.1.1** Criar `admin/src/components/sisreg-console/detail-panel.tsx` — `"use client"`:
  - Input de código (regulation code)
  - Toggle JSON/PDF (format)
  - Botão "Buscar"
  - Se JSON: renderiza resposta em JsonViewer com botão copiar
  - Se PDF: faz download do blob (`apiClient.getBlob()`) com `URL.createObjectURL` → `<a download>`
  - Profile-aware: usa endpoint de videofonista ou solicitante conforme store
  - Para solicitante: adiciona `operator_cnes` param do store

- **2.2.1.2** Criar `admin/src/app/sisreg/consulta/page.tsx` — `"use client"`:
  - Toggle principal: Search/Detail (2 tabs ou toggle switch)
  - Tab Search: `SearchPanel`
  - Tab Detail: `DetailPanel`

- **2.2.1.3** Teste: `admin/tests/integration/pages/sisreg-console-detail.test.tsx` — busca por código, toggle JSON/PDF

---

## Fase 3 — Profile Settings

### 3.1 Zustand Store

- **3.1.1.1** Criar `admin/src/stores/profile-store.ts`:
  - State: `{ profile: "videofonista" | "solicitante"; operators: string[]; videofonistas: string[]; operatorState: string; videofonistState: string; operatorList: Operator[]; videofonistList: Videofonista[] }`
  - Actions: `setProfile(p)`, `setOperators(ops)`, `setVideofonistas(vids)`, `setOperatorState(s)`, `setVideofonistState(s)`, `setOperatorList(list)`, `setVideofonistList(list)`
  - Persistence: `persist` middleware do Zustand com `localStorage` storage
  - Storage key: `regulahub-profile` (compatível com NiceGUI keys para migração transparente)
- **3.1.1.2** Teste: `admin/tests/unit/stores/profile-store.test.ts` — set/get cada campo, persistence funciona (mock localStorage)

### 3.2 Hooks de Operadores

- **3.2.1.1** Criar `admin/src/hooks/use-operators.ts` — `useQuery` que chama `GET /raw/operators`, popula store com `setOperatorList`
- **3.2.1.2** Criar `admin/src/hooks/use-videofonistas.ts` — `useQuery` que chama `GET /raw/videofonistas`, popula store com `setVideofonistList`
- **3.2.1.3** Criar `admin/src/hooks/use-validate-credentials.ts` — `useMutation` que chama `POST /raw/validate-credentials` para cada username, retorna array de `CredentialValidation`

### 3.3 Componentes

- **3.3.1.1** Criar `admin/src/components/profile-settings/profile-selector.tsx` — `"use client"`:
  - 2 cards clicáveis: Videofonista (ícone headset, amber quando ativo), Solicitante (ícone assignment, blue quando ativo)
  - Card ativo: borda 2px na cor do perfil, sombra, ícone check
  - onClick: `setProfile()` no store

- **3.3.1.2** Criar `admin/src/components/profile-settings/user-list-with-checkboxes.tsx` — `"use client"`:
  - Props genéricas: `{ items: T[]; selectedKeys: string[]; onSelectionChange: (keys: string[]) => void; getKey: (item: T) => string; columns: { key: string; label: string }[]; stateFilter?: { value: string; onChange: (v: string) => void; options: { label: string; value: string }[] } }`
  - Filtro de estado no topo (Select)
  - Botões "Selecionar Todos" / "Desmarcar Todos"
  - Lista com Checkbox por item, colunas configuráveis
  - Filtra items por estado selecionado

- **3.3.1.3** Criar `admin/src/components/profile-settings/credential-validator.tsx` — `"use client"`:
  - Props: `{ usernames: string[]; profileType: string }`
  - Botão "Validar Credenciais"
  - Usa `useValidateCredentials` mutation
  - Loading: spinner por username
  - Resultado: ícone ✓ (verde) ou ✗ (vermelho) por username, tooltip com erro
  - Contador: "X/Y válidos"

- **3.3.1.4** Criar `admin/src/components/profile-settings/videofonista-section.tsx` — `"use client"`:
  - Usa `useVideofonistas()` hook para carregar lista
  - Extrai opções de estado da lista (`_extract_state_options`)
  - UserListWithCheckboxes com columns: [username, state]
  - CredentialValidator para selecionados
  - Botão "Salvar" → persiste no store
  - Validação: todos do mesmo estado, todos do mesmo sistema

- **3.3.1.5** Criar `admin/src/components/profile-settings/operator-section.tsx` — `"use client"`:
  - Mesma estrutura da videofonista-section mas com columns: [unit_name, cnes, username]
  - Usa `useOperators()` hook
  - Mesmas validações

#### 3.3.2 Página

- **3.3.2.1** Criar `admin/src/app/sisreg/profile/page.tsx` — `"use client"`:
  - ProfileSelector no topo
  - Se videofonista: VideofonistSection
  - Se solicitante: OperatorSection
  - Transição suave ao trocar perfil

- **3.3.2.2** Teste: `admin/tests/integration/pages/profile-settings.test.tsx` — seleção de perfil, checkboxes, validação de credenciais (MSW mock)

---

## Fase 4 — Polish e Cutover

### 4.1 Testes E2E

- **4.1.1.1** Criar `admin/tests/e2e/dashboard.spec.ts` — fluxo: abrir /, verificar KPIs, trigger sync, verificar status atualiza
- **4.1.1.2** Criar `admin/tests/e2e/appointments.spec.ts` — fluxo: buscar por data, verificar tabela, clicar detalhe, export Excel
- **4.1.1.3** Criar `admin/tests/e2e/sisreg-console.spec.ts` — fluxo: filtrar, ver resultados, toggle table/json, buscar detalhe
- **4.1.1.4** Criar `admin/tests/e2e/profile-settings.spec.ts` — fluxo: selecionar perfil, escolher operadores, salvar
- **4.1.1.5** Criar `admin/tests/e2e/navigation.spec.ts` — fluxo: navegar por todas as páginas via sidebar, verificar títulos
- **4.1.1.6** Criar `admin/tests/e2e/i18n.spec.ts` — fluxo: mudar idioma no header, verificar que labels mudam em todas as páginas

### 4.2 Auditoria

- **4.2.1.1** Executar `pnpm build` — verificar zero erros TypeScript
- **4.2.1.2** Executar `pnpm lint` — verificar zero warnings/errors ESLint
- **4.2.1.3** Executar `pnpm test` — all pass (unit + integration)
- **4.2.1.4** Executar `pnpm test:e2e` — all pass (Playwright)
- **4.2.1.5** Executar Lighthouse audit via Playwright — Performance ≥ 90, Accessibility ≥ 95
- **4.2.1.6** Verificar responsividade: testar em 3 viewports (375px mobile, 768px tablet, 1440px desktop) — sem overflow, sidebar colapsa, tabelas scrollam
- **4.2.1.7** Verificar i18n: navegar todas as 15 páginas em cada um dos 3 idiomas — nenhum key literal visível

### 4.3 Cutover

- **4.3.1.1** Editar `docker-compose.yml` — substituir serviço `admin` (NiceGUI) pelo `admin-next`: alterar profile de `admin-next` para `admin`, porta 3000→8080 ou manter 3000
- **4.3.1.2** Remover diretório `src/regulahub/admin/` inteiro (11 arquivos Python)
- **4.3.1.3** Editar `pyproject.toml` — remover dependências: `nicegui`, `openpyxl`
- **4.3.1.4** Editar `Dockerfile.dev` — remover qualquer referência ao admin NiceGUI
- **4.3.1.5** Atualizar `CLAUDE.md`:
  - Stack: adicionar "Next.js 15, React 19, TypeScript, shadcn/ui, TanStack Query, Zustand" na seção Stack
  - Remover seção "Admin UI (NiceGUI)"
  - Adicionar seção "Admin UI (Next.js)" com nova estrutura de diretórios
  - Atualizar comandos: `pnpm --prefix admin dev`, `pnpm --prefix admin test`, `pnpm --prefix admin build`
  - Atualizar Docker: profile `admin` agora é Next.js
- **4.3.1.6** Atualizar `docs/specs/TECH_SPEC.md` — nova seção Admin UI com stack Next.js
- **4.3.1.7** Atualizar `docs/architecture/ARCHITECTURE_DIAGRAM.md` — diagrama de componentes reflete Next.js
- **4.3.1.8** Atualizar `docs/specs/features/V1_LOCAL_PIPELINE.md` — referências ao admin
- **4.3.1.9** Executar `poetry install` — verificar que nicegui e openpyxl foram removidos
- **4.3.1.10** Executar `poetry run pytest tests/ -v` — all pass (remover/atualizar `test_admin_smoke.py` se necessário)
- **4.3.1.11** Executar `docker compose --profile admin up -d` — admin Next.js healthy na porta configurada
- **4.3.1.12** Smoke test manual: navegar pelas 7 páginas funcionais, verificar dados, trigger sync, export Excel

---

## Verificação Final

Após conclusão de todas as fases:

```bash
# Backend
poetry run pytest tests/ -v                    # All pass
poetry run ruff check src/ tests/              # Clean
poetry run bandit -c pyproject.toml -r src/    # Clean

# Frontend
cd admin
pnpm lint                                      # Clean
pnpm build                                     # Zero TypeScript errors
pnpm test                                      # All pass (unit + integration)
pnpm test:e2e                                  # All pass (Playwright)

# Docker
docker compose up -d                           # Postgres + API healthy
docker compose --profile admin up -d           # Admin Next.js healthy
curl http://localhost:8000/health              # 200
curl http://localhost:3000                     # 200 (or configured port)
```
