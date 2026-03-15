# Perfil Solicitante/Executante

## Objetivo

Adicionar suporte ao perfil **Solicitante/Executante** do SisReg III, permitindo coletar agendamentos com visão por unidade de saúde. Este perfil complementa o Videofonista (visão estadual) e é necessário porque o Videofonista não enxerga todos os agendamentos — há divergências significativas em relação aos dados de referência (planilha xlsx).

## Contexto

### Por que outro perfil?

O Videofonista tem visão estadual mas não retorna todos os agendamentos. O Solicitante/Executante tem visão limitada à sua unidade, mas combinando dados de operadores de todas as 7 unidades, conseguimos cobertura completa.

### Diferenças entre perfis

| Aspecto | Videofonista | Solicitante/Executante |
|---------|--------------|------------------------|
| Visão | Estadual (todos os municípios) | Limitada à unidade do operador |
| Menu | `li[3]` | `li[5]` → submenu `li[5] > ul > li[2]` |
| Filtro por procedimento | Sim (`co_pa_interno`) | Não |
| Exportação CSV/TXT | A verificar | Sim (menu "Consulta Amb → Arquivo Agendamentos") |
| Restrição de horário | Nenhuma | Bloqueio 8h-15h (SisReg retorna mensagem de erro) |
| Operadores necessários | 1 (visão global) | 1 por unidade (7 unidades = 7 operadores) |
| Capabilities | `["read"]` | `["read"]` (write existe no SisReg mas NÃO implementamos) |

### Unidades mapeadas (Amazonas)

1. TELEMEDICINA-CAIC DRA MARIA HELENA FREITAS DE GOES
2. TELEMEDICINA-POLICLINICA CODAJAS
3. TELEMEDICINA-POLICLINICA JOAO DOS SANTOS BRAGA
4. TELEMEDICINA-POLICLINICA ZENO LANZINI
5. TELEMEDICINA-SPA E POLICLINICA DR JOSE LINS
6. TELEMEDICINA-COMPLEXO REGULADOR DO AMAZONAS
7. TELEMEDICINA-AMBULATORIO VIRTUAL DO AMAZONAS

## Endpoints

### Endpoints Raw (1:1 com SisReg)

```text
GET /raw/solicitante/appointments?date={dd/MM/yyyy}
GET /raw/solicitante/appointments/{code}
GET /raw/solicitante/export?start_date={dd/MM/yyyy}&end_date={dd/MM/yyyy}&format={csv|txt}
```

### Regulation Controller (orquestração)

```text
GET /regulation/appointments?date={YYYY-MM-DD}&mode=solicitante
GET /regulation/appointments?codigo={code}&mode=solicitante
```

O parâmetro `mode` é opcional. Default: valor de `SISREG_PROFILE` no .env.

## Configuração Multi-Operador

### Env var `OPERATORS_JSON`

Array JSON com 1 operador por unidade:

```json
[
  {
    "username": "34953924835-TATIANA",
    "password": "708090",
    "profile": "SOLICITANTE",
    "unit_name": "TELEMEDICINA-CAIC DRA MARIA HELENA FREITAS DE GOES",
    "unit_cnes": "0000000"
  }
]
```

Reutiliza modelos existentes: `Operator` e `Unit` de `src/regulahub/models/operator.py`.

Os CNES codes são extraídos via script `scripts/extract_cnes.py` (login em cada operador → parse do HTML → extrai CNES).

## Fluxo Interno

### Listagem (modo Solicitante)

1. Carregar lista de operadores de `OPERATORS_JSON`
2. Para cada operador (serial, um por vez):
   a. Login no SisReg com credenciais do operador
   b. Navegar ao menu de agendamentos via `li[5]` → submenu `li[5] > ul > li[2]`
   c. Aplicar filtros (data, situação=7, sem `co_pa_interno`)
   d. Parsear tabela de resultados (`.table_listagem`)
   e. Iterar todas as páginas
   f. Logout
3. Deduplicar agendamentos por código (cross-operator)
4. Pular operadores cuja unidade (CNES) já foi processada

### Exportação CSV/TXT

1. Login com operador da unidade
2. Navegar ao endpoint CGI de exportação (a ser descoberto na Fase 1)
3. Retornar o response body do SisReg como StreamingResponse (pass-through)
4. Content-Type: `text/csv` ou `text/plain` conforme parâmetro `format`

### Detalhe (via Videofonista — encadeamento dual-profile)

**REGRA CRÍTICA:** O perfil Solicitante/Executante **NÃO** consegue buscar detalhes de agendamentos emitidos por outras unidades. A pesquisa por código retorna "nenhum registro encontrado" se o agendamento não pertence à unidade do operador.

Por isso, a busca de detalhes deve usar o perfil **Videofonista**, que tem visão estadual e pode resolver qualquer código.

### Arquitetura de Encadeamento (Dual-Profile)

O fluxo encadeado (regulation controller) usa **ambos os perfis** para cobertura completa:

```text
┌─────────────────────────────────────────────────────────┐
│ FASE 1: Coleta (Solicitante — por unidade)              │
│                                                          │
│ Para cada operador/unidade:                             │
│   POST /cgi-bin/expo_solicitacoes (CSV)                 │
│   → Exporta TODOS os agendamentos da unidade            │
│   → Extrai códigos de solicitação do CSV                │
│                                                          │
│ Consolidar: deduplicar códigos de todas as unidades     │
├─────────────────────────────────────────────────────────┤
│ FASE 2: Detalhes (Videofonista — visão estadual)        │
│                                                          │
│ Para cada código de solicitação:                        │
│   GET detalhe via Videofonista (visão estadual)         │
│   → Retorna dados completos independente da unidade     │
└─────────────────────────────────────────────────────────┘
```

**Por que não usar só Videofonista?** Porque o Videofonista filtra por procedimento (`co_pa_interno`) e não retorna todos os agendamentos — há divergências significativas vs dados de referência.

**Por que não usar só Solicitante?** Porque o Solicitante só vê agendamentos da sua própria unidade e não consegue buscar detalhes de agendamentos de outras unidades por código.

## Restrição de Horário

- O perfil Executante tem funcionalidades bloqueadas entre **8h e 15h**
- O SisReg retorna uma **mensagem de erro no HTML** quando acessado nesse horário
- O scrapper deve detectar essa mensagem e lançar `TimeRestrictionError`
- O handler retorna **HTTP 503** com body informativo:

```json
{
  "detail": "SisReg functionality unavailable during restricted hours (8h-15h)"
}
```

## Strategy Pattern

### SolicitanteStrategy

```text
profile_type: SOLICITANTE
menu_selector: #barraMenu > ul > li:nth-child(5) > a
submenu_selector: #barraMenu > ul > li:nth-child(5) > ul > li:nth-child(2) > a
filters: etapa, tipo_periodo, dt_inicial, dt_final, cmb_situacao, qtd_itens_pag (SEM co_pa_interno)
capabilities: ["read"]
```

EXECUTANTE mapeia para a mesma strategy (perfis idênticos no SisReg para fins de leitura).

## Regras de Negócio

- NUNCA executar ações de escrita (autorizar, cancelar, agendar) — SOMENTE LEITURA
- NUNCA fazer mais de uma sessão simultânea por operador
- Pular operadores da mesma unidade já processada (dedup por CNES)
- Operadores com login inválido: logar warning e pular (não interromper)
- Sessão expirada: re-autenticar e retomar (até 3 tentativas)
- Processar operadores serialmente (evitar bloqueio pelo SisReg)

## Tratamento de Erros

| Cenário | HTTP Status | Descrição |
|---------|-------------|-----------|
| Login falhou (operador individual) | — | Logar warning, pular para próximo operador |
| Todos os logins falharam | 401 | Nenhum operador conseguiu autenticar |
| Sessão expirada | 503 | Após 3 tentativas de reconexão |
| Horário bloqueado (8h-15h) | 503 | Funcionalidade indisponível no horário |
| Nenhum operador configurado | 500 | `OPERATORS_JSON` vazio ou ausente |
| Perfil não implementado | 501 | ProfileType não suportado |

## Critérios de Aceite

- [ ] `SolicitanteStrategy` registrada e resolvida pelo registry
- [ ] `ExecutanteStrategy` mapeia para mesma implementação
- [ ] Menu `li[5]` + submenu `li[5] > ul > li[2]` navegados corretamente
- [ ] Filtros NÃO incluem `co_pa_interno`
- [ ] `OPERATORS_JSON` parseado corretamente de env var
- [ ] Multi-operador: itera 7 operadores, deduplicação por CNES
- [ ] Operadores com login inválido são pulados sem interromper
- [ ] Restrição de horário detectada e retorna 503
- [ ] Backward compatibility: endpoints existentes inalterados
- [ ] `GET /regulation/appointments?date=...&mode=solicitante` retorna dados consolidados
- [ ] `GET /regulation/appointments?date=...` sem `mode` usa default do config
- [ ] Exportação CSV/TXT retorna response do SisReg como pass-through
- [ ] Testes unitários para strategy, config, operator_service
- [ ] Testes de integração para regulation dual-mode
- [ ] Todos os testes existentes continuam passando
