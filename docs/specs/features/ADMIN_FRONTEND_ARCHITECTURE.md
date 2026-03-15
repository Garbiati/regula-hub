# Arquitetura do Admin Frontend — Guia Normativo

> **Audiência:** Humanos e agentes de IA que desenvolvem o admin UI.
> **Status:** Aprovado — todo código novo DEVE seguir estas normas.
> **Última revisão:** 2026-03-14

---

## Sumário

1. [Diagnóstico de Fragilidades](#1-diagnóstico-de-fragilidades)
2. [Plano de Melhorias](#2-plano-de-melhorias)
3. [Normas de Arquitetura](#3-normas-de-arquitetura)
4. [Convenções por Camada](#4-convenções-por-camada)
5. [Checklist para Novas Telas](#5-checklist-para-novas-telas)
6. [Anti-Padrões Proibidos](#6-anti-padrões-proibidos)

---

## 1. Diagnóstico de Fragilidades

Análise completa do frontend em `admin/src/` (~4.400 linhas, 44+ componentes, 12 hooks).

### 1.1 Violações de DRY (Don't Repeat Yourself)

| ID | Problema | Arquivos Afetados | Impacto |
|----|----------|-------------------|---------|
| **DRY-01** | `MetadataField` duplicado identicamente | `credential-form-dialog.tsx:213-220`, `credential-detail-dialog.tsx:298-305` | Qualquer mudança de estilo exige edição em 2 arquivos |
| **DRY-02** | `FilterField` (label + children wrapper) local em `filter-card.tsx:42-49` | Mesmo padrão em `credentials-table.tsx`, `detail-panel.tsx`, `credential-form-dialog.tsx` — cada um reimplementa `<label> + <div>` | 4+ implementações distintas do mesmo layout |
| **DRY-03** | Spinner inline `<Loader2 className="mr-2 h-4 w-4 animate-spin" />` | `credential-form-dialog.tsx` (×2), `credential-detail-dialog.tsx` (×3), `sync-trigger.tsx` (×1) | 6+ cópias idênticas do mesmo markup |
| **DRY-04** | Validation result inline (CheckCircle/XCircle + text) | `credential-form-dialog.tsx:119-136`, `credential-detail-dialog.tsx:203-218` | Bloco de ~15 linhas 100% duplicado |
| **DRY-05** | Padrão `<label className="text-xs/text-sm font-medium text-[var(--text-secondary/primary)]">` | 12+ locais em dialogs, filter-card, credentials-table, detail-panel | Sem componente `<FormLabel>` padronizado |

### 1.2 Violações de KISS (Keep It Simple, Stupid)

| ID | Problema | Local | Complexidade Desnecessária |
|----|----------|-------|---------------------------|
| **KISS-01** | `useFetchDetail` é um hook imperativo com `useState` + `useCallback` manualmente | `hooks/use-fetch-detail.ts` (84 linhas) | Deveria ser `useQuery` + `useMutation` como os outros 11 hooks — quebra o padrão mental |
| **KISS-02** | `CredentialDetailDialog` tem 7 `useState` + lógica de view/edit no mesmo componente | `credential-detail-dialog.tsx` (345 linhas) | Dialog tenta ser viewer E editor ao mesmo tempo — viola Single Responsibility |
| **KISS-03** | `I18nProvider` recarrega a página inteira para trocar idioma | `providers/i18n-provider.tsx:41` (`window.location.reload()`) | Perde estado de formulários, scroll, e selections — UX ruim |
| **KISS-04** | `camelizeKeys<T>()` aplicado a TODA resposta HTTP silenciosamente | `lib/api-client.ts:44` | Dev lê docs da API em snake_case mas os tipos são camelCase — confusão garantida para novos devs |

### 1.3 Violações de SOLID

| Princípio | ID | Problema | Local |
|-----------|-----|----------|-------|
| **S** (Single Responsibility) | **SRP-01** | `CredentialDetailDialog` é viewer + editor + validator em 345 linhas | `credential-detail-dialog.tsx` |
| **S** | **SRP-02** | `SearchPanel` gerencia filtros + busca + detalhe + export + view mode | `sisreg-console/search-panel.tsx` |
| **O** (Open-Closed) | **OCP-01** | Novos sistemas (ESUS, SIGA, CARE, SER) requerem copiar páginas placeholder manualmente | `app/esus-regulacao/`, `app/siga-saude/`, etc. — 8 páginas quase idênticas |
| **D** (Dependency Inversion) | **DIP-01** | `useFetchDetail` chama `apiClient` diretamente em vez de usar abstração TanStack Query | `hooks/use-fetch-detail.ts` |
| **I** (Interface Segregation) | **ISP-01** | `StatusBadge` recebe `t` (toda a função de tradução) quando precisa apenas de 5 strings | `credential-detail-dialog.tsx:307` |

### 1.4 Problemas de Clean Code

| ID | Problema | Local | Impacto |
|----|----------|-------|---------|
| **CC-01** | Magic strings para status: `"idle"`, `"checking"`, `"valid"` — sem enum exportado | `credential-detail-dialog.tsx:35` | Type-unsafe, não reutilizável |
| **CC-02** | `ExcelExportButton` recebe `data as unknown as Record<string, unknown>[]` — casting forçado | `search-panel.tsx:113` | Indica tipagem fraca no componente de export |
| **CC-03** | `data?.appointments ?? []` repetido 3× no mesmo componente | `search-panel.tsx` | Deveria ser variável local |
| **CC-04** | `profile !== "videofonista"` hardcoded em 3 hooks/componentes | `use-fetch-detail.ts:30`, `search-panel.tsx`, `detail-panel.tsx` | Lógica de negócio espalhada — deveria ser método no store ou util |
| **CC-05** | Console.error em hooks (`console.error("Detail fetch failed:", err)`) | `use-fetch-detail.ts:48,73` | Deveria usar error reporting estruturado, não console |

### 1.5 Problemas de Design Patterns

| ID | Problema | Padrão Recomendado |
|----|----------|--------------------|
| **DP-01** | Dialogs controlados via `useState` no parent + prop drilling `open`/`onClose` | **Compound Component Pattern** — Dialog gerencia seu próprio estado via `DialogTrigger` |
| **DP-02** | Ausência de Error Boundaries por feature — apenas 1 global | **Error Boundary per feature** — isola falhas |
| **DP-03** | Sem padrão de composição para "Titled Section" (label + conteúdo + borda) | **Compound/Slot Pattern** — `<Section>`, `<Section.Title>`, `<Section.Content>` |
| **DP-04** | Placeholder pages são 8 arquivos com ~10 linhas cada, quase idênticos | **Dynamic Route** — `[system]/consulta/page.tsx` com lookup |

---

## 2. Plano de Melhorias

### Princípios do Plano

- **Zero breaking changes** — cada item é independente e compatível com o código atual
- **Incremental** — cada fase pode ser mergeada separadamente
- **Testável** — os 64 testes existentes devem continuar passando após cada fase

### Fase 1 — Extrair Componentes Compartilhados (DRY)

> **Risco:** Nenhum — extração pura, sem mudança de comportamento.
> **Estimativa de arquivos modificados:** ~10

| Task | O que fazer | Arquivos |
|------|-------------|----------|
| 1.1 | Extrair `MetadataField` para `components/shared/metadata-field.tsx` | Criar 1, editar 2 (credential dialogs) |
| 1.2 | Extrair `FormField` (label + children) para `components/shared/form-field.tsx` | Criar 1, editar 4+ (filter-card, credential dialogs, credentials-table, detail-panel) |
| 1.3 | Extrair `ButtonSpinner` para `components/shared/button-spinner.tsx` — inline `Loader2` wrapper | Criar 1, editar 3+ (credential dialogs, sync-trigger) |
| 1.4 | Extrair `ValidationResult` (icon + text para valid/invalid) para `components/shared/validation-result.tsx` | Criar 1, editar 2 (credential dialogs) |
| 1.5 | Extrair `StatusBadge` de `credential-detail-dialog.tsx` para `components/shared/status-badge.tsx` | Criar 1, editar 1 |

### Fase 2 — Padronizar Hooks (KISS + DIP)

> **Risco:** Baixo — interfaces públicas dos hooks são preservadas.
> **Estimativa de arquivos modificados:** ~4

| Task | O que fazer | Arquivos |
|------|-------------|----------|
| 2.1 | Reescrever `useFetchDetail` como `useQuery` + `useMutation` seguindo o padrão dos outros 11 hooks | Editar `use-fetch-detail.ts`, `search-panel.tsx`, `detail-panel.tsx` |
| 2.2 | Extrair lógica `profile !== "videofonista"` para helper `isOperatorRequired(profile)` em `lib/utils.ts` | Criar helper, editar 3 hooks/componentes |

### Fase 3 — Simplificar Componentes Complexos (SRP)

> **Risco:** Médio — requer atenção ao estado interno dos componentes.
> **Estimativa de arquivos modificados:** ~5

| Task | O que fazer | Arquivos |
|------|-------------|----------|
| 3.1 | Dividir `CredentialDetailDialog` em `CredentialViewDialog` + `CredentialEditDialog` | Criar 2, editar 1 (credentials-table.tsx que renderiza o dialog) |
| 3.2 | Mover `StatusBadge` type `ValidationStatus` para `types/credential.ts` como enum | Editar 2 |

### Fase 4 — Rotas Dinâmicas (OCP)

> **Risco:** Baixo — os placeholders atuais são triviais.
> **Estimativa de arquivos modificados:** ~10 (deletar 8, criar 2)

| Task | O que fazer | Arquivos |
|------|-------------|----------|
| 4.1 | Criar rota dinâmica `[system]/profile/page.tsx` e `[system]/consulta/page.tsx` | Criar 2 |
| 4.2 | Deletar 8 páginas placeholder duplicadas | Deletar 8 em `esus-regulacao/`, `siga-saude/`, `care-parana/`, `ser-rj/` |
| 4.3 | Atualizar `constants.ts` com type-safe system lookup | Editar 1 |

### Fase 5 — Error Boundaries por Feature

> **Risco:** Nenhum — adição pura.

| Task | O que fazer | Arquivos |
|------|-------------|----------|
| 5.1 | Criar `FeatureErrorBoundary` com retry button e error code | Criar 1 |
| 5.2 | Envolver cada feature section (Dashboard, Credentials, Console) com boundary | Editar 3 pages |

### Ordem de Execução Recomendada

```
Fase 1 (DRY)  →  branch: refactor/extract-shared-components
Fase 2 (Hooks) →  branch: refactor/standardize-hooks
Fase 3 (SRP)  →  branch: refactor/split-credential-dialog
Fase 4 (OCP)  →  branch: refactor/dynamic-system-routes
Fase 5 (Error) →  branch: feat/feature-error-boundaries
```

Cada fase é um PR separado para `dev`. Cada PR deve:
1. Passar todos os 64+ testes existentes
2. Incluir testes para componentes novos
3. Não alterar comportamento visível ao usuário

---

## 3. Normas de Arquitetura

### 3.1 Estrutura de Diretórios

```
admin/src/
├── app/                        # Rotas (App Router). APENAS layout e composição.
│   ├── layout.tsx              # Root layout — providers + shell
│   ├── page.tsx                # Dashboard
│   ├── settings/page.tsx
│   └── [system]/               # Rotas dinâmicas por sistema regulatório
│       ├── credentials/page.tsx
│       ├── profile/page.tsx
│       └── consulta/page.tsx
│
├── components/
│   ├── ui/                     # Primitivos shadcn/base-ui — NÃO colocar lógica de negócio aqui
│   ├── shared/                 # Componentes reutilizáveis com lógica leve (FormField, MetadataField, etc.)
│   ├── layout/                 # Shell: Header, Sidebar, NavItem, NavGroup
│   ├── dashboard/              # Componentes do Dashboard
│   ├── credentials/            # Componentes de credenciais
│   ├── sisreg-console/         # Componentes do console SisReg
│   └── profile-settings/       # Componentes de perfil e seleção de usuários
│
├── hooks/                      # Custom hooks — TODOS devem usar TanStack Query
├── stores/                     # Zustand stores — APENAS estado global cross-page
├── types/                      # Interfaces TypeScript (1 arquivo por domínio)
├── lib/                        # Utilitários puros (sem React, sem side effects)
├── providers/                  # React Context providers
└── i18n/                       # Configuração de internacionalização
```

### 3.2 Regra de Ouro: Cada Camada Tem Sua Responsabilidade

| Camada | Faz | NÃO faz |
|--------|-----|---------|
| `app/` (pages) | Compõe components, define layout da página | Lógica de negócio, fetch de dados, useState complexo |
| `components/ui/` | Renderiza UI genérica, aceita props de estilo | Fetch, hooks de dados, acesso ao store |
| `components/shared/` | Componentes reutilizáveis com lógica leve | Fetch direto, lógica de domínio específico |
| `components/{feature}/` | Compõe UI + hooks para uma feature | Fetch direto — delega para hooks |
| `hooks/` | Encapsula TanStack Query (queries + mutations) | Renderização, UI state (useState) |
| `stores/` | Estado global cross-page (profile, system) | UI state local (dialog open, form values) |
| `lib/` | Funções puras, constantes, configurações | React hooks, componentes, side effects |
| `types/` | Interfaces e enums TypeScript | Implementação, lógica |

---

## 4. Convenções por Camada

### 4.1 Hooks (`hooks/`)

**Regra: TODO hook de dados DEVE usar TanStack Query.**

```typescript
// ✅ CORRETO — usa useQuery
export function useCredentials(system: string) {
  return useQuery({
    queryKey: ["admin", "credentials", "list", system],
    queryFn: () => apiClient.get<CredentialListResponse>(`/api/admin/credentials/${system}`),
    enabled: !!system,
  });
}

// ✅ CORRETO — usa useMutation
export function useCreateCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CredentialCreate) => apiClient.post("/api/admin/credentials", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "credentials"] });
    },
  });
}

// ❌ PROIBIDO — useState + useCallback manual para dados do servidor
export function useFetchDetail() {
  const [data, setData] = useState(null);   // ← NÃO
  const [loading, setLoading] = useState(false); // ← NÃO
  const fetch = useCallback(async () => { ... }); // ← NÃO
}
```

**Naming:**
- Queries: `use{Recurso}` → `useCredentials`, `useSyncStatus`
- Mutations: `use{Ação}{Recurso}` → `useCreateCredential`, `useTriggerSync`
- Query keys: via factory `queryKeys` de `lib/query-keys.ts` (ver seção 4.12)

### 4.2 Components (`components/`)

**Regra: Componentes de feature NÃO fazem fetch direto — usam hooks.**

```typescript
// ✅ CORRETO — componente de feature usa hook
export function WorkerStatus() {
  const { data, isLoading } = useSyncStatus();
  if (isLoading) return <Skeleton />;
  return <Card>...</Card>;
}

// ❌ PROIBIDO — fetch direto no componente
export function WorkerStatus() {
  const [data, setData] = useState(null);
  useEffect(() => { fetch("/api/...").then(setData) }, []); // ← NÃO
}
```

**Tamanho máximo:** Se um componente ultrapassar **200 linhas**, ele DEVE ser dividido.

**Regra de extração:** Se um bloco JSX é usado **2+ vezes** (mesmo entre arquivos diferentes), ele DEVE ser extraído para `components/shared/`.

**Naming:**
- Arquivos: `kebab-case.tsx` → `metadata-field.tsx`
- Componentes: `PascalCase` → `MetadataField`
- Props: `{ComponentName}Props` → `MetadataFieldProps`

### 4.3 Shared Components (`components/shared/`)

Componentes nesta pasta DEVEM:
1. Ser **genéricos** — não podem depender de tipos de domínio específico
2. Ter **props tipadas** com interface exportada
3. Aceitar `className` para customização via Tailwind
4. Ser **documentados** com JSDoc mínimo (uma linha descrevendo o propósito)

```typescript
// ✅ CORRETO — shared component genérico
interface FormFieldProps {
  label: string;
  children: React.ReactNode;
  className?: string;
}

/** Label + conteúdo wrapper para formulários. */
export function FormField({ label, children, className }: FormFieldProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <label className="text-xs text-[var(--text-secondary)]">{label}</label>
      {children}
    </div>
  );
}
```

### 4.4 UI Components (`components/ui/`)

**Regra: Esta pasta é EXCLUSIVA para primitivos shadcn/base-ui.**

- NUNCA adicionar lógica de negócio
- NUNCA importar hooks de dados (`use-credentials`, etc.)
- NUNCA importar do store
- Modificações permitidas: estilo, variantes, acessibilidade

### 4.5 Pages (`app/`)

**Regra: Pages são composição pura.**

```typescript
// ✅ CORRETO — page compõe componentes
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">{t("dash.title")}</h1>
      <WorkerStatus />
      <ExecutionSummary />
      <SyncTrigger />
    </div>
  );
}

// ❌ PROIBIDO — lógica direta na page
export default function DashboardPage() {
  const [data, setData] = useState(null);
  useEffect(() => { ... }, []);  // ← NÃO — mover para hook ou componente
}
```

### 4.6 Store (`stores/`)

**Regra: Store é APENAS para estado que persiste entre páginas.**

| Tipo de estado | Onde armazenar | Exemplo |
|----------------|---------------|---------|
| Sistema/perfil/estado ativo | Zustand store | `profile-store.ts` |
| Dialog open/close | `useState` local no componente | `const [open, setOpen] = useState(false)` |
| Form values | `useState` local no componente | `const [form, setForm] = useState({...})` |
| Server data | TanStack Query (cache automático) | `useCredentials()` |
| URL state (filtros, paginação) | `useSearchParams` ou URL | Futuro: filtros de busca |

### 4.7 Types (`types/`)

**Regra: 1 arquivo por domínio, enums exportados, sem implementação.**

```typescript
// ✅ types/credential.ts
export interface Credential { ... }
export interface CredentialCreate { ... }
export type ValidationStatus = "idle" | "checking" | "valid" | "invalid" | "error";

// ❌ PROIBIDO — type definido localmente no componente
// credential-detail-dialog.tsx
type ValidationStatus = "idle" | "checking" | ...  // ← mover para types/
```

### 4.8 Lib (`lib/`)

**Regra: Funções puras, sem React, sem side effects.**

```typescript
// ✅ CORRETO — função pura
export function isOperatorRequired(profile: string): boolean {
  return profile !== "videofonista";
}

// ❌ PROIBIDO — hook em lib/
export function useFormatDate() { ... } // ← mover para hooks/
```

### 4.9 Estilização

**Regra: CSS variables para theming, Tailwind classes para layout.**

```typescript
// ✅ CORRETO — usa CSS variables do design system
<p className="text-[var(--text-secondary)]">...</p>

// ✅ CORRETO — usa Tailwind para layout
<div className="flex items-center gap-4 p-4">

// ❌ PROIBIDO — cores hardcoded
<p className="text-gray-500">...</p>        // ← usar var(--text-secondary)
<p style={{ color: "#636366" }}>...</p>     // ← NUNCA inline style

// ❌ PROIBIDO — Tailwind arbitrário para cores do design system
<p className="text-[#374151]">...</p>       // ← usar a CSS variable
```

### 4.10 Internacionalização (i18n)

**Regra: NENHUMA string visível ao usuário hardcoded no JSX.**

```typescript
// ✅ CORRETO
const t = useTranslations();
<p>{t("credentials.no_results")}</p>

// ❌ PROIBIDO
<p>No results found</p>
```

**Chaves de tradução:** formato `{domínio}.{chave}` em snake_case.
- `nav.dashboard`, `dash.worker_status`, `credentials.col_username`, `api.search`

### 4.11 Error Handling

**Regra: Usar `showErrorToast()` para erros de mutação, Error Boundary para erros de render.**

```typescript
// ✅ CORRETO — mutation com error handling
useMutation({
  mutationFn: ...,
  onError: (err) => {
    const code = err instanceof ApiError ? ERROR_CODES.CRED_CREATE_FAILED : ERROR_CODES.GEN_UNEXPECTED;
    showErrorToast(code, t("credentials.error_creating"));
  },
});

// ❌ PROIBIDO — console.error como tratamento
catch (err) {
  console.error("Failed:", err); // ← nunca como tratamento principal
}
```

---

## 5. Checklist para Novas Telas

Antes de criar qualquer nova tela ou componente, verifique:

### Antes de Codar

- [ ] Existe uma spec em `docs/specs/features/`? Se não, crie uma primeiro.
- [ ] Li as normas de arquitetura neste documento.
- [ ] Identifiquei quais componentes de `shared/` posso reutilizar.
- [ ] Identifiquei quais hooks existentes posso reutilizar.

### Estrutura

- [ ] Page (`app/`) contém APENAS composição de componentes.
- [ ] Componentes de feature estão em `components/{feature}/`.
- [ ] Componentes reutilizáveis estão em `components/shared/`.
- [ ] Nenhum componente excede 200 linhas.
- [ ] Nenhum componente helper definido localmente que já existe em `shared/`.

### Dados

- [ ] Todo fetch de dados usa hook TanStack Query em `hooks/`.
- [ ] Nenhum `useState` + `useEffect` para server data.
- [ ] Query keys seguem o padrão: `["admin", domain, action, ...params]`.
- [ ] Mutations invalidam queries relevantes no `onSuccess`.

### Estilo

- [ ] Todas as cores usam CSS variables (`var(--text-primary)`, etc.).
- [ ] Nenhuma cor hexadecimal hardcoded no JSX.
- [ ] Nenhum `style={{}}` inline.
- [ ] Componentes glass usam as utility classes (`glass-card`, etc.).

### Tipagem

- [ ] Props interface exportada com nome `{Component}Props`.
- [ ] Types de domínio em `types/`, não locais.
- [ ] Nenhum `as unknown as ...` casting.
- [ ] Nenhuma magic string — usar const ou enum de `types/` ou `lib/`.

### i18n

- [ ] Todas as strings visíveis ao usuário passam por `t()`.
- [ ] Novas chaves adicionadas nos 3 locales (`pt-BR.json`, `en-US.json`, `es-AR.json`).

### Testes

- [ ] Componente novo tem teste unitário em `tests/unit/`.
- [ ] Hook novo tem teste em `tests/unit/` ou `tests/integration/`.
- [ ] Testes existentes continuam passando (`pnpm --prefix admin test`).
- [ ] Build compila sem erros (`pnpm --prefix admin build`).

---

### 4.12 Query Key Standards (`lib/query-keys.ts`)

**Regra: Toda query key DEVE vir da factory centralizada em `lib/query-keys.ts`.**

```typescript
// ✅ CORRETO — usar factory
import { queryKeys } from "@/lib/query-keys";

useQuery({ queryKey: queryKeys.admin.credentials.list(system), ... });
useQuery({ queryKey: queryKeys.sisreg.search(profile, selectedUsers, filters), ... });

// ❌ PROIBIDO — key literal inline
useQuery({ queryKey: ["admin", "credentials", "list", system], ... });
```

**Regras de composição:**
- Padrão: `[domain, resource, action, ...params]`
- TODO parâmetro que afeta a request (filtros, operadores selecionados) DEVE estar na key
- Invalidação DEVE ser o mais específica possível — usar `queryKeys.admin.credentials.all` como prefix somente quando necessário

### 4.13 Store Design Rules (Zustand)

**Regra: Server data NÃO vai no Zustand — usar React Query cache.**

```typescript
// ✅ CORRETO — Zustand para estado cross-page de UI
interface ProfileState {
  system: string;
  profile: string;
  selectedUsers: string[];
}

// ❌ PROIBIDO — server data no Zustand
interface ProfileState {
  userList: Credential[];     // ← Isso pertence ao React Query cache
  setUserList: (l) => void;   // ← Side effect em queryFn para popular
}
```

**Persist DEVE ter `version` + `migrate`** para evitar dados stale no localStorage:

```typescript
persist(
  (set) => ({ ... }),
  { name: "regulahub-profile", version: 1 },
)
```

**ZERO side effects em `queryFn`** — não chamar store setters, toasts, ou outros efeitos dentro de `queryFn`. Usar `onSuccess`/`onError` da mutation ou `select` da query.

### 4.14 Type System Rules (`types/`)

**Regra: Types DEVEM estar em `types/` — nunca inline em hooks ou componentes.**

```typescript
// ✅ CORRETO — tipo em types/credential.ts, importado pelo hook
import type { CredentialValidation } from "@/types/credential";

// ❌ PROIBIDO — tipo inline no hook
interface ValidateCredentialResult { ... } // ← Duplicação inevitável
```

- Sem aliases não usados — limpar dead types regularmente
- Response types DEVEM ter campos tipados — proibido `Record<string, string>` para estruturas conhecidas
- Um tipo canônico por conceito — sem duplicatas entre arquivos

### 4.15 Testing Conventions

**Regras obrigatórias:**
- Todo hook novo DEVE ter teste unitário com `renderHook` + `createWrapper()` de `tests/unit/hook-test-utils.tsx`
- Fixtures usam factory functions (`makeCredential()`, `makeSyncExecution()`) — proibido `as never` casting
- MSW handlers em `tests/mocks/handlers.ts` DEVEM cobrir todos os endpoints usados por hooks
- Features com CRUD DEVEM ter integration test do fluxo completo
- Shared components DEVEM ter pelo menos 1 teste unitário por componente

**Meta de cobertura:** 70% hooks, 60% componentes

---

## 6. Anti-Padrões Proibidos

### Código

| Anti-Padrão | Motivo | Alternativa |
|-------------|--------|-------------|
| `useState` + `useEffect` para server data | Não tem cache, retry, dedup, stale handling | `useQuery` do TanStack Query |
| Definir componente helper local (`function X() {}`) que já existe em `shared/` | Duplicação | Importar de `shared/` |
| Componente com 7+ `useState` | Complexidade excessiva — viola SRP | Dividir em subcomponentes ou usar `useReducer` |
| `console.error` como error handling | Invisível ao usuário, não estruturado | `showErrorToast()` + error boundary |
| `as unknown as T` casting | Mascara erros de tipagem | Corrigir o type na origem |
| Cores hardcoded (`#636366`, `text-gray-500`) | Fora do design system | CSS variables (`var(--text-secondary)`) |
| String visível hardcoded | Impede internacionalização | `t("chave.da.string")` |
| Prop drilling de 3+ níveis | Dificulta manutenção | Zustand store ou Context |
| `window.location.reload()` para state changes | Perde estado do app | React state management |

### Arquitetura

| Anti-Padrão | Motivo | Alternativa |
|-------------|--------|-------------|
| Lógica de negócio em `components/ui/` | UI primitivos devem ser genéricos | Mover para `components/{feature}/` |
| Fetch direto em componente (`fetch()`, `apiClient.get()`) | Sem cache, sem loading/error handling uniforme | Hook TanStack Query |
| Lógica condicional por profile espalhada (`profile !== "videofonista"`) | Lógica de negócio duplicada | Helper function em `lib/utils.ts` |
| Copiar página placeholder para cada sistema | Violação de OCP | Rota dinâmica `[system]/` |
| 1 Error Boundary para o app inteiro | Uma falha derruba tudo | Error Boundary por feature section |
| Types definidos localmente em componentes | Não reutilizável, duplicação | `types/{domínio}.ts` |

### Data Layer (Novos)

| Anti-Padrão | Motivo | Alternativa |
|-------------|--------|-------------|
| Side effects em `queryFn` (store setters, toasts) | Viola contrato React Query — `queryFn` deve ser puro | `onSuccess`/`onError` na mutation, ou `select` na query |
| Server data no Zustand (`userList`) | Duplica cache do React Query, fica stale | Ler do React Query cache via hook |
| `invalidateQueries` broad sem scoping | Invalida queries não relacionadas, causa refetch desnecessário | Usar keys específicas da factory |
| `version` ausente no Zustand persist | Dados stale do localStorage podem quebrar a app | Sempre incluir `version: N` + `migrate` |
| `onError={() => {}}` em providers sem logging | Erros engolidos silenciosamente | Handler que loga ou usa error boundary |
| Strings hardcoded (EN ou PT-BR) fora de locale files | Impede internacionalização | Sempre usar `t("chave")` via `next-intl` |
| Query keys inline (`["admin", "credentials"]`) | Inconsistência, typos, duplicação | Factory `queryKeys` de `lib/query-keys.ts` |
| Hook morto (0 imports) persistindo no codebase | Dead code confunde devs e aumenta bundle | Deletar imediatamente |

---

## Referência Rápida — Onde Colocar Cada Coisa

```
"Preciso fazer fetch de dados"          → hooks/use-{recurso}.ts (useQuery)
"Preciso mutar dados"                   → hooks/use-{ação}-{recurso}.ts (useMutation)
"Preciso de um botão/input/dialog"      → components/ui/ (shadcn primitivo)
"Preciso de label+input wrapper"        → components/shared/form-field.tsx
"Preciso de um card com KPI"            → components/shared/kpi-card.tsx
"Preciso de uma tabela com sorting"     → components/shared/data-table.tsx
"Preciso de estado cross-page"          → stores/ (Zustand)
"Preciso de estado local de form"       → useState() no componente
"Preciso de uma constante/config"       → lib/constants.ts
"Preciso de um type/interface"          → types/{domínio}.ts
"Preciso de uma função utilitária"      → lib/utils.ts (ou lib/{nome}.ts se grande)
"Preciso de uma nova página"            → app/{rota}/page.tsx (composição pura)
"Preciso de componentes da feature X"   → components/{feature-name}/
```

---

## 7. Lições Aprendidas (Auditoria 2026-03-15)

Erros identificados na auditoria e regras derivadas para prevenir recorrência.

| Erro | Regra Derivada |
|------|----------------|
| `fetch()` sem timeout no `ApiClient` | Toda chamada `fetch` DEVE ter `AbortSignal.timeout(30_000)` |
| API key com fallback vazio (`?? ""`) | Credenciais NUNCA devem ter fallback silencioso — throw se ausente |
| i18n double-render (import estático no layout + dinâmico no provider) | Usar pattern oficial do `next-intl` — carregar mensagens uma única vez |
| `window.location.reload()` para trocar locale | Gerenciar locale via React state — nunca reload completo |
| Mutation `onError` descarta `ApiError.detail` | `onError` DEVE capturar e exibir `ApiError.detail` quando disponível |
| Cache times hardcoded em hooks individuais | Centralizar em `lib/constants/cache.ts` |
| Form submit sem validação de `userId` | Desabilitar submit quando dados obrigatórios (como `userId`) estão ausentes |
| `onError={() => {}}` no `NextIntlClientProvider` | Handler DEVE logar o erro — nunca engolir silenciosamente |
