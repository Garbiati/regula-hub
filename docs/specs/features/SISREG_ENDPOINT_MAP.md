# Mapeamento de Endpoints CGI do SisReg III

> Capturado via Chrome extension em 2026-03-07.
> Perfil: EXECUTANTE/SOLICITANTE — Unidade: COMPLEXO REGULADOR DO AMAZONAS (CNES 5726832)

## Regra Crítica de Visibilidade

**Solicitante/Executante só retorna agendamentos da própria unidade.** Pesquisa por código de solicitação retorna "nenhum registro encontrado" se o agendamento foi emitido por outra unidade. Apenas o **Videofonista** (visão estadual) pode resolver qualquer código independente da unidade de origem.

**Impacto na arquitetura:**

- **Endpoints raw** → 1:1 com SisReg, retornam dados conforme o perfil permite
- **Endpoints encadeados** (regulation controller) → usam **ambos** os perfis:
  1. Solicitante (por unidade): exporta CSV → coleta todos os códigos
  2. Videofonista (estadual): busca detalhes por código

## Menu Principal (perfil Executante/Solicitante)

| # | Menu | Submenu | Endpoint CGI | Descrição |
|---|------|---------|-------------|-----------|
| 1 | solicitar | — | `/cgi-bin/cadweb50?url=/cgi-bin/marcar` | Criar solicitação (write) |
| 2 | Cancelar Solicitações | — | `/cgi-bin/cons_verificar` | Cancelar solicitações (write) |
| 3 | cadastro » | Preparos | `/cgi-bin/config_preparo` | Configurar preparos |
| 4 | consulta geral » | CNS | `/cgi-bin/cadweb50?standalone=1` | Consulta CNS no CadWeb |
| 5 | consulta amb » | Impressao/Confirmacao de Agendas | `/cgi-bin/cons_agendas` | Agendas |
| 5 | consulta amb » | **Solicitações** | `/cgi-bin/gerenciador_solicitacao` | **Listagem principal** |
| 5 | consulta amb » | Agendamentos/Data Solicitação | `/cgi-bin/rellst.pl` | Ranking |
| 5 | consulta amb » | Agendados pela Fila de Espera | `/cgi-bin/cons_fila_espera` | Marcados fila |
| 5 | consulta amb » | Agendados pela Regulação | `/cgi-bin/cons_marcados_reg` | Marcados regulador |
| 5 | consulta amb » | Devolvidos pela Regulação | `/cgi-bin/cons_negados_reg` | Devolvidos |
| 5 | consulta amb » | PPI/Cotas | `/cgi-bin/cons_ppi_cotas` | Cotas |
| 5 | consulta amb » | Unidades | `/cgi-bin/cons_unidade` | Consulta unidades |
| 5 | consulta amb » | Escalas | `/cgi-bin/cons_escalas` | Horários |
| 5 | consulta amb » | Grupos/Procedimentos | `/cgi-bin/cons_pa` | Procedimentos |
| 5 | consulta amb » | Tabela SIGTAP | `/cgi-bin/cons_procedimento.pl` | Tabela SIGTAP |
| 5 | consulta amb » | Prontuários a Enviar | `/cgi-bin/cons_prontuario_enviar` | Prontuários envio |
| 5 | consulta amb » | Prontuários a Receber | `/cgi-bin/cons_prontuario_receber` | Prontuários recebimento |
| 5 | consulta amb » | Solicitações Pendentes na Fila | `/cgi-bin/cons_pendente_fila_` | Pendentes na fila |
| 5 | consulta amb » | **Arquivo Agendamento (txt)** | `/cgi-bin/expo_solicitacoes` | **Exportação TXT/CSV** |
| 5 | consulta amb » | CNS | `/cgi-bin/cadweb50?standalone=1` | Consulta CNS |
| 5 | consulta amb » | Solicitações não confirmadas/Unidade | `/cgi-bin/rel_amb_faltas_sol.pl` | Relatório faltas |
| 6 | bpa » | geração de arquivo bpa (txt) | `/cgi-bin/expo_bpa_v2` | Exportação BPA |
| 6 | bpa » | Consulta bpa gerado | `/cgi-bin/cons_bpa_v2` | Consulta BPA |
| 7 | Logoff Videofonista | — | `/cgi-bin/ctrl_videofonista` | Logoff videofonista |

### Links de Navegação (header)

| Link | Endpoint |
|------|----------|
| Principal | `/` |
| Perfil | `/cgi-bin/config_perfil` |
| Sair | `?logout=1` |
| Acesso a Api | `https://wiki.saude.gov.br/SISREG/...` |

---

## Gerenciador de Solicitações (`/cgi-bin/gerenciador_solicitacao`)

Endpoint principal de listagem para perfil Solicitante/Executante.

### Seletores CSS de Navegação

```
Menu: #barraMenu > ul > li:nth-child(5) > a  ("consulta amb")
Submenu: #barraMenu > ul > li:nth-child(5) > ul > li:nth-child(2) > a  ("Solicitações")
```

### Parâmetros do Formulário

| Campo | Name | Tipo | Descrição |
|-------|------|------|-----------|
| Etapa | `etapa` | hidden | `LISTAR_SOLICITACOES` (ao submeter) |
| Cód. Solicitação | `co_solicitacao` | text | Código da solicitação |
| CNS Paciente | `cns_paciente` | text | Cartão Nacional de Saúde |
| Nome Paciente | `no_usuario` | text | Nome do paciente |
| CNES Solicitante | `cnes_solicitante` | text | CNES da unidade solicitante |
| CNES Executante | `cnes_executante` | text | CNES da unidade executante |
| Cód. Unificado | `co_proc_unificado` | text | Código unificado do procedimento |
| Cód. Interno | `co_pa_interno` | text | Código interno do procedimento |
| Descrição | `ds_procedimento` | text | Descrição do procedimento |
| Tipo de Pesquisa | `tipo_periodo` | radio | S/A/E/P/C |
| Data Inicial | `dt_inicial` | text | dd/MM/yyyy |
| Data Final | `dt_final` | text | dd/MM/yyyy |
| Situação | `cmb_situacao` | select | Dinâmico por tipo_periodo |
| Itens por Página | `qtd_itens_pag` | select | 10/20/50/100/0(TODOS) |
| Sequência | `co_seq_solicitacao` | hidden | — |
| Ordenação | `ordenacao` | hidden | Default: 2 |
| Página | `pagina` | hidden | Default: 0 |

### Tipo de Pesquisa (`tipo_periodo`)

| Valor | Label | Descrição |
|-------|-------|-----------|
| S | Solicitação | Data da solicitação |
| A | Agendamento | Data do agendamento |
| E | Execução | Data de execução |
| P | Confirmação | Data de confirmação |
| C | Cancelamento | Data de cancelamento |

### Situação (`cmb_situacao`) — carrega dinâmico por tipo_periodo

#### tipo_periodo = S (Solicitação) — COMPLETO

| Valor | Label |
|-------|-------|
| 1 | Solicitação / Pendente / Regulação |
| 2 | Solicitação / Pendente / Fila de Espera |
| 3 | Solicitação / Cancelada |
| 4 | Solicitação / Devolvida |
| 5 | Solicitação / Reenviada |
| 6 | Solicitação / Negada |
| 7 | Solicitação / Agendada |
| 9 | Solicitação / Agendada / Fila de Espera |
| 10 | Agendamento / Cancelado |
| 11 | Agendamento / Confirmado |
| 12 | Agendamento / Falta |

#### tipo_periodo = A (Agendamento) — st_agend=true

| Valor | Label |
|-------|-------|
| 7 | Solicitação / Agendada |
| 9 | Solicitação / Agendada / Fila de Espera |
| 10 | Agendamento / Cancelado |
| 11 | Agendamento / Confirmado |
| 12 | Agendamento / Falta |

#### tipo_periodo = E (Execução) — st_exec=true

| Valor | Label |
|-------|-------|
| 7 | Solicitação / Agendada |
| 9 | Solicitação / Agendada / Fila de Espera |
| 10 | Agendamento / Cancelado |
| 11 | Agendamento / Confirmado |
| 12 | Agendamento / Falta |

#### tipo_periodo = P (Confirmação) — st_conf=true

| Valor | Label |
|-------|-------|
| 11 | Agendamento / Confirmado |

#### tipo_periodo = C (Cancelamento) — st_cancel=true

| Valor | Label |
|-------|-------|
| 3 | Solicitação / Cancelada |
| 10 | Agendamento / Cancelado |

### Botão PESQUISAR

```javascript
onclick="buscaSolicitacoes(1);"
```

### URL de Exemplo (GET)

```
/cgi-bin/gerenciador_solicitacao?etapa=LISTAR_SOLICITACOES&co_solicitacao=&cns_paciente=&no_usuario=&cnes_solicitante=&cnes_executante=&co_proc_unificado=&co_pa_interno=&ds_procedimento=&tipo_periodo=A&dt_inicial=01%2F03%2F2026&dt_final=07%2F03%2F2026&cmb_situacao=7&qtd_itens_pag=20&co_seq_solicitacao=&ordenacao=2&pagina=0
```

---

## Exportar Agenda (`/cgi-bin/expo_solicitacoes`)

Endpoint de exportação de agendamentos em TXT ou CSV.

### Parâmetros do Formulário

| Campo | Name | Tipo | Descrição |
|-------|------|------|-----------|
| Data Inicial | `data1` | text | dd/MM/yyyy |
| Data Final | `data2` | text | dd/MM/yyyy |
| Profissional | `cpf` | select | CPF do profissional (opcional, valor "0" = todos) |
| Procedimento | `procedimento` | select | Código do procedimento (dinâmico, carrega após selecionar profissional) |
| Formato | `tp_arquivo` | select | 0 = TXT, 1 = CSV |
| Etapa | `etapa` | hidden | `exportar` |
| Unidade | `unidade` | hidden | CNES da unidade (auto-preenchido pela sessão) |

### Botão Exportar

```javascript
onclick="exportar();"
```

### Resposta CSV (tp_arquivo=1)

- **Método:** POST
- **Content-Type:** `application/x-www-form-urlencoded`
- **Resposta:** Arquivo CSV com separador `;` (ponto-e-vírgula)
- **Encoding:** verificar (provavelmente ISO-8859-1 ou UTF-8)

#### Colunas do CSV (38 colunas, separador `;`)

| # | Coluna | Descrição | PII? |
|---|--------|-----------|------|
| 1 | `solicitacao` | Código da solicitação | |
| 2 | `codigo_interno` | Código interno do procedimento | |
| 3 | `codigo_unificado` | Código SIGTAP | |
| 4 | `descricao_procedimento` | Nome do procedimento | |
| 5 | `cpf_proficional_executante` | CPF do profissional executante | **SIM** |
| 6 | `nome_profissional_executante` | Nome do profissional | |
| 7 | `data_agendamento` | Data do agendamento | |
| 8 | `hr_agendamento` | Hora do agendamento | |
| 9 | `tipo` | Tipo | |
| 10 | `cns` | Cartão Nacional de Saúde | **SIM** |
| 11 | `nome` | Nome do paciente | **SIM** |
| 12 | `dt_nascimento` | Data de nascimento | **SIM** |
| 13 | `idade` | Idade (anos) | |
| 14 | `idade_meses` | Idade (meses) | |
| 15 | `nome_mae` | Nome da mãe | **SIM** |
| 16 | `tipo_logradouro` | Tipo de logradouro | **SIM** |
| 17 | `logradouro` | Logradouro | **SIM** |
| 18 | `complemento` | Complemento | **SIM** |
| 19 | `numero_logradouro` | Número | **SIM** |
| 20 | `bairro` | Bairro | **SIM** |
| 21 | `cep` | CEP | **SIM** |
| 22 | `telefone` | Telefone | **SIM** |
| 23 | `municipio` | Município do paciente | |
| 24 | `ibge` | Código IBGE do município | |
| 25 | `mun_solicitante` | Município solicitante | |
| 26 | `ibge_solicitante` | IBGE do município solicitante | |
| 27 | `cnes_solicitante` | CNES da unidade solicitante | |
| 28 | `unidade_fantasia` | Nome fantasia da unidade | |
| 29 | `sexo` | Sexo do paciente | |
| 30 | `data_solicitacao` | Data da solicitação | |
| 31 | `operador_solicitante` | Operador que solicitou | |
| 32 | `data_autorizacao` | Data de autorização | |
| 33 | `operador_autorizador` | Operador que autorizou | |
| 34 | `valor_procedimento` | Valor do procedimento (R$) | |
| 35 | `situacao` | Situação atual do agendamento | |
| 36 | `cid` | Código CID | |
| 37 | `cpf_profissional_solicitante` | CPF do profissional solicitante | **SIM** |
| 38 | `nome_profissional_solicitante` | Nome do profissional solicitante | |

> **Nota:** Fixture do header em `tests/fixtures/export_csv_header.csv`
> Captura: 562 registros retornados para CNES 5726832, período 25/02-06/03/2026

### Observações

- O campo `cpf` (Profissional) é **opcional** — funciona sem selecionar profissional
- O campo `procedimento` carrega **dinamicamente** ao selecionar o profissional
- O campo `unidade` é preenchido automaticamente com o CNES da sessão logada
- Suporta exportação em TXT (valor 0) e CSV (valor 1)
- **Coluna-chave para encadeamento:** `solicitacao` = código da solicitação (usado para buscar detalhes via Videofonista)
