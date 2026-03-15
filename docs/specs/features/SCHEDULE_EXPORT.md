# Exportação de Agendamentos via CSV do SisReg (Arquivo Agendamento)

> **Status:** Em implementação
> **Autor:** Alessandro
> **Data:** 2026-03-19

## 1. Contexto

O sistema atual busca agendamentos via scraping HTML do SisReg (`/cgi-bin/gerenciador_solicitacao`), o que dispara reCAPTCHA após muitas requisições. O SisReg possui um endpoint alternativo — **"Arquivo Agendamento (TXT)"** (`/cgi-bin/expo_solicitacoes`) — que exporta um CSV com **38 colunas** e separador `;` em uma única requisição por unidade.

**Ganho:** Elimina o problema de reCAPTCHA ao substituir N requests (listagem + N detalhes) por 1 request de exportação por unidade. O CSV já traz dados completos (nome mãe, telefone, CPF profissional, endereço, etc.).

**Perfil requerido:** EXECUTANTE/SOLICITANTE (equivalentes para este endpoint).

## 2. Contrato do Endpoint SisReg

### 2.1 Request

```
POST /cgi-bin/expo_solicitacoes
Content-Type: application/x-www-form-urlencoded
```

| Parâmetro     | Tipo   | Obrigatório | Descrição                                |
|---------------|--------|-------------|------------------------------------------|
| `data1`       | string | Sim         | Data início (dd/MM/yyyy)                 |
| `data2`       | string | Sim         | Data fim (dd/MM/yyyy)                    |
| `cpf`         | string | Não         | CPF do profissional ("0" = todos)         |
| `procedimento`| string | Não         | Código do procedimento (vazio = todos)   |
| `tp_arquivo`  | int    | Sim         | 0 = TXT (tab), 1 = CSV (`;`)            |
| `etapa`       | string | Sim         | Sempre `"exportar"`                      |
| `unidade`     | hidden | —           | Auto-preenchido pela sessão SisReg       |

### 2.2 Response

- **Content-Type:** `text/csv` ou `text/plain`
- **Encoding:** UTF-8 com CRLF line terminators
- **Separador:** `;` (CSV) ou `\t` (TXT)
- **Header:** Primeira linha contém os 38 nomes de coluna

### 2.3 Schema das 38 Colunas

| #  | Nome da Coluna                      | Tipo   | PII  | Descrição                          |
|----|-------------------------------------|--------|------|------------------------------------|
| 1  | `solicitacao`                       | string | —    | Código da solicitação (chave dedup)|
| 2  | `codigo_interno`                    | string | —    | Código interno do procedimento     |
| 3  | `codigo_unificado`                  | string | —    | Código unificado SIGTAP            |
| 4  | `descricao_procedimento`            | string | —    | Nome do procedimento               |
| 5  | `cpf_proficional_executante`        | string | PII  | CPF do profissional (com typo)     |
| 6  | `nome_profissional_executante`      | string | —    | Nome do profissional executante    |
| 7  | `data_agendamento`                  | string | —    | Data agendamento (dd.MM.yyyy)      |
| 8  | `hr_agendamento`                    | string | —    | Hora do agendamento (HH:mm)        |
| 9  | `tipo`                              | string | —    | Tipo                               |
| 10 | `cns`                               | string | PII  | CNS do paciente                    |
| 11 | `nome`                              | string | PII  | Nome do paciente                   |
| 12 | `dt_nascimento`                     | string | PII  | Data nascimento (dd.MM.yyyy)       |
| 13 | `idade`                             | string | —    | Idade em anos                      |
| 14 | `idade_meses`                       | string | —    | Idade em meses                     |
| 15 | `nome_mae`                          | string | PII  | Nome da mãe                        |
| 16 | `tipo_logradouro`                   | string | PII  | Tipo logradouro (RUA, AV, etc)     |
| 17 | `logradouro`                        | string | PII  | Nome do logradouro                 |
| 18 | `complemento`                       | string | PII  | Complemento do endereço            |
| 19 | `numero_logradouro`                 | string | PII  | Número do endereço                 |
| 20 | `bairro`                            | string | PII  | Bairro                             |
| 21 | `cep`                               | string | PII  | CEP                                |
| 22 | `telefone`                          | string | PII  | Telefone(s) do paciente            |
| 23 | `municipio`                         | string | —    | Município                          |
| 24 | `ibge`                              | string | —    | Código IBGE do município           |
| 25 | `mun_solicitante`                   | string | —    | Município solicitante              |
| 26 | `ibge_solicitante`                  | string | —    | IBGE do município solicitante      |
| 27 | `cnes_solicitante`                  | string | —    | CNES da unidade solicitante        |
| 28 | `unidade_fantasia`                  | string | —    | Nome fantasia da unidade           |
| 29 | `sexo`                              | string | —    | Sexo (M/F)                         |
| 30 | `data_solicitacao`                  | string | —    | Data da solicitação (dd.MM.yyyy)   |
| 31 | `operador_solicitante`              | string | —    | CPF-Nome do operador solicitante   |
| 32 | `data_autorizacao`                  | string | —    | Data da autorização (dd.MM.yyyy)   |
| 33 | `operador_autorizador`              | string | —    | Nome-CPF do autorizador            |
| 34 | `valor_procedimento`                | string | —    | Valor do procedimento (R$)         |
| 35 | `situacao`                          | string | —    | Situação (PENDENTE, etc)           |
| 36 | `cid`                               | string | —    | Código CID                         |
| 37 | `cpf_profissional_solicitante`      | string | PII  | CPF do profissional solicitante    |
| 38 | `nome_profissional_solicitante`     | string | —    | Nome do profissional solicitante   |

> **Nota:** Coluna 5 tem typo intencional (`cpf_proficional_executante`) — preservar como está.
> **Nota:** Datas usam ponto como separador (`dd.MM.yyyy`), não barra.

## 3. Endpoints da API

### 3.1 Busca JSON

```
POST /api/admin/sisreg/schedule-export
```

**Request body:**
```json
{
  "date_from": "19/03/2026",
  "date_to": "31/03/2026",
  "profile_type": "SOLICITANTE",
  "usernames": ["operator1", "operator2"],
  "procedure_filter": "TELECONSULTA",
  "enrich": false
}
```

**Response:** `ScheduleExportListResponse` (JSON) ou `EnrichedExportListResponse` se `enrich=true`

### 3.2 Download CSV

```
POST /api/admin/sisreg/schedule-export/csv
```

Mesmo body → `StreamingResponse` com `Content-Disposition: attachment`

### 3.3 Download TXT

```
POST /api/admin/sisreg/schedule-export/txt
```

Mesmo body → `StreamingResponse` com `Content-Disposition: attachment`

## 4. Fluxo de Orquestração Multi-Operador

```
1. Recebe request com lista de usernames
2. Resolve credenciais por username (profile SOLICITANTE)
3. Para cada operador em paralelo (Semaphore(5)):
   a. Login no SisReg com perfil SOLICITANTE
   b. POST /cgi-bin/expo_solicitacoes com filtros de data
   c. Parse do CSV retornado
   d. Retorna lista de ScheduleExportRow
4. Merge todos os resultados
5. Deduplica por campo `solicitacao` (first-seen wins)
6. Se procedure_filter: filtra por descricao_procedimento (case-insensitive)
7. Se enrich=true: enriquece com CADSUS (CPF, email, etc)
8. Retorna ScheduleExportResponse
```

## 5. Enriquecimento CADSUS (Opcional)

O CSV do SisReg **não contém o CPF do paciente**. A integração CADSUS busca:
- CPF, email, telefone, nome mãe/pai, raça, CNS definitivo, endereço

**Fluxo:**
1. Filtra rows por procedimento (se filtro fornecido)
2. Extrai CNS únicos das rows filtradas
3. Busca CADSUS em paralelo (Semaphore(10)) com cache por CNS
4. Mescla dados CADSUS nos rows → EnrichedExportRow

**API CADSUS:**
- Token: `GET https://ehr-auth.saude.gov.br/api/osb/token` → JWT
- Dados: `POST https://servicos.saude.gov.br/cadsus/v2/PDQSupplierJWT` → SOAP XML HL7 v3

## 6. Critérios de Aceite

- [ ] CSV de exportação é parseado corretamente com 38 colunas
- [ ] Multi-operador: login paralelo, merge e deduplicação por `solicitacao`
- [ ] Falha de um operador não bloqueia os demais (retorna dados parciais)
- [ ] Endpoint JSON retorna subset de colunas (sem PII de endereço)
- [ ] Endpoints CSV/TXT retornam arquivo completo para download
- [ ] Filtro por procedimento funciona (case-insensitive)
- [ ] Enriquecimento CADSUS preenche CPF paciente quando habilitado
- [ ] CADSUS desabilitado → retorna rows sem enriquecimento
- [ ] PII nunca logada em plaintext
- [ ] Rate limiting em todos os endpoints
- [ ] Auth obrigatório (`X-API-Key`)
- [ ] Frontend: formulário com filtros, tabela de resultados, download CSV/TXT
- [ ] i18n em 3 idiomas (pt-BR, en-US, es-AR)
