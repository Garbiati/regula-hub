# Validação de Credenciais SisReg

## Visão Geral

Endpoint e botão na UI admin para validar credenciais SisReg de videofonistas e operadores solicitantes, testando login real no SisReg III.

## Motivação

Credenciais de múltiplos estados/operadores podem expirar ou ser invalidadas sem aviso. A validação proativa evita falhas silenciosas no pipeline de sincronização e nos endpoints da API.

## Endpoint

### `POST /raw/validate-credentials`

**Autenticação:** `X-API-Key` (router-level dependency).

**Request:**

```json
{
  "username": "vf_am_user",
  "profile_type": "videofonista"
}
```

| Campo | Tipo | Validação |
|-------|------|-----------|
| `username` | string | 1-100 chars, obrigatório |
| `profile_type` | string | `videofonista` ou `solicitante` |

**Response:**

```json
{
  "username": "vf_am_user",
  "valid": true,
  "error": null
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `username` | string | Usuário validado |
| `valid` | bool | `true` se login SisReg bem-sucedido |
| `error` | string \| null | Código do erro (se `valid=false`) |

**Códigos de erro:**

| Código | Descrição |
|--------|-----------|
| `not_configured` | Usuário não encontrado em `OPERATORS_JSON`/`VIDEOFONISTAS_JSON` |
| `invalid_credentials` | Login SisReg retornou erro (`LoginError`) |
| `connection_error` | Falha de conexão HTTP com SisReg |

### Fluxo

1. Busca o usuário em `VideofonistasSettings` ou `OperatorsSettings` pelo `username`
2. Se não encontrado → `{"valid": false, "error": "not_configured"}`
3. Cria `SisregSession(base_url, username, password)`, tenta `login()`
4. `LoginError` → `{"valid": false, "error": "invalid_credentials"}`
5. `httpx.HTTPError` → `{"valid": false, "error": "connection_error"}`
6. Sucesso → `{"valid": true}`

**Segurança:** A senha nunca aparece no request ou response. O endpoint apenas confirma se o login funciona.

## Admin UI

### Botão "Validar credenciais"

Adicionado nas seções Videofonista e Solicitante da página `/sisreg/profile`:

- **Coluna Status** (28px, última coluna) — inicialmente vazia
- **Botão** no footer, ao lado de "Salvar"
- **Fluxo ao clicar:**
  1. Botão desabilitado (loading)
  2. Para cada usuário visível, sequencialmente:
     - Spinner na coluna status
     - `POST /raw/validate-credentials` com `{username, profile_type}`
     - Spinner substituído por ícone verde (`check_circle`) ou vermelho (`cancel`) com tooltip
  3. Botão reabilitado, notificação com resumo (`"3/5 credenciais válidas"`)
- Status resetado ao trocar estado (container reconstruído por `_render_vf_list`/`_render_op_list`)

## Remoção de Campos Legados

### `SisregSettings`

Campos `username`, `password`, `profile` removidos. Apenas `base_url` permanece.

### Migração dos Consumidores

| Arquivo | Antes | Depois |
|---------|-------|--------|
| `api/deps.py` | `sisreg.username/password` | Primeiro videofonista de `VIDEOFONISTAS_JSON` |
| `worker/managed_session.py` | `SisregSettings` direto | Parâmetros explícitos no construtor |
| `worker/pipeline.py` | `ManagedSession()` | `ManagedSession(base_url, username, password)` |

### Variáveis de Ambiente

Removidas do `.env.example`:
- `SISREG_USERNAME`
- `SISREG_PASSWORD`
- `SISREG_PROFILE`

Mantida: `SISREG_BASE_URL`

## Dados Multi-Estado

### Novos estados (dados fictícios para desenvolvimento)

| UF | Videofonista | Operador | Unidade | CNES |
|----|-------------|----------|---------|------|
| SP | `vf_sp_demo` | `sol_sp_demo` | UBS VILA MARIANA | `9999901` |
| RJ | `vf_rj_demo` | `sol_rj_demo` | UBS COPACABANA | `9999902` |
| MG | `vf_mg_demo` | `sol_mg_demo` | UBS SAVASSI | `9999903` |

Credenciais fictícias — falharão na validação com SisReg real.

## Critérios de Aceitação

- [ ] `POST /raw/validate-credentials` retorna `valid: true/false` com código de erro
- [ ] Endpoint protegido por `X-API-Key`
- [ ] Senha nunca exposta em request/response
- [ ] Botão "Validar credenciais" na UI funciona para ambos os perfis
- [ ] Estado selecionado no dropdown filtra corretamente os usuários validados
- [ ] `SisregSettings` não contém mais `username/password/profile`
- [ ] Pipeline e API continuam funcionando via `VIDEOFONISTAS_JSON`
- [ ] `.env.example` atualizado sem variáveis legadas
