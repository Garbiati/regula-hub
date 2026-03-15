# Raw Videofonista Pass-Through

> Spec para refatorar os endpoints raw do Videofonista para pass-through 1:1 com o SisReg.

## Objetivo

Os endpoints `/raw/videofonista/appointments` e `/raw/videofonista/appointments/{code}` devem ser **pass-through 1:1** com o SisReg III — uma única requisição HTTP, com todos os parâmetros do formulário web expostos, sem lógica de negócio adicional (sem iteração por procedimentos, sem deduplicação, sem filtro de teleconsulta, sem paginação automática).

## Motivação

Os endpoints atuais usam `AppointmentService`, que embute lógica de negócio:
- Iteração por códigos de procedimento
- Deduplicação por código de solicitação
- Filtro client-side de teleconsulta
- Paginação automática (busca todas as páginas)
- Retry com Tenacity

O objetivo raw é expor o SisReg **como ele é**, permitindo que o consumidor controle todos os parâmetros.

## Parâmetros do Formulário SisReg

### Endpoint de Listagem

`GET /cgi-bin/gerenciador_solicitacao`

| Parâmetro | Tipo | Obrigatório | Default | Validação |
|-----------|------|-------------|---------|-----------|
| `dt_inicial` | string | Sim | — | `dd/MM/yyyy` |
| `dt_final` | string | Sim | — | `dd/MM/yyyy` |
| `tipo_periodo` | string | Não | `"A"` | `S\|A\|E\|P\|C` |
| `cmb_situacao` | string | Não | `"7"` | `1-12` |
| `qtd_itens_pag` | string | Não | `"0"` | `10\|20\|50\|100\|0` |
| `pagina` | string | Não | `"0"` | numérico |
| `ordenacao` | string | Não | `"2"` | numérico |
| `co_solicitacao` | string | Não | `""` | maxlen 10 |
| `cns_paciente` | string | Não | `""` | maxlen 15 |
| `no_usuario` | string | Não | `""` | maxlen 250 |
| `cnes_solicitante` | string | Não | `""` | maxlen 7 |
| `cnes_executante` | string | Não | `""` | maxlen 7 |
| `co_proc_unificado` | string | Não | `""` | maxlen 10 |
| `co_pa_interno` | string | Não | `""` | maxlen 7 |
| `ds_procedimento` | string | Não | `""` | maxlen 250 |

Parâmetros fixos (não expostos):
- `etapa=LISTAR_SOLICITACOES` (sempre)
- `co_seq_solicitacao=""` (sempre vazio)

## Modelo de Resposta

### Listagem (`RawListAppointmentsResponse`)

```json
{
  "appointments": [...],
  "total": 20,
  "current_page": 1,
  "total_pages": 5
}
```

- `appointments`: lista de `Appointment` (mesmo modelo existente)
- `total`: quantidade de registros **nesta página** (não total geral)
- `current_page`: página atual (1-based, SisReg usa 0-based internamente)
- `total_pages`: total de páginas (extraído do HTML via `parse_total_pages`)

### Detalhe (`AppointmentDetailResponse`)

Sem alteração — mesmo modelo existente.

## Comportamento

### O que NÃO faz (diferença do `AppointmentService`)

- **Não itera** por códigos de procedimento
- **Não deduplica** registros
- **Não filtra** por teleconsulta
- **Não pagina** automaticamente (retorna apenas a página solicitada)

### O que FAZ

- Login + navegação ao menu (via `get_sisreg_navigator`)
- Monta os params exatamente como o formulário web
- Faz uma única requisição GET ao SisReg
- Parseia o HTML com `parse_appointment_list` / `parse_total_pages`
- Retry com Tenacity em `SessionExpiredError` (3 tentativas, backoff exponencial 2-10s)

## Critérios de Aceitação

1. Todos os parâmetros do formulário SisReg são expostos como query params
2. Parâmetros opcionais são enviados como string vazia quando não fornecidos
3. Parâmetros obrigatórios (`dt_inicial`, `dt_final`) são validados por regex
4. Resposta inclui metadados de paginação (`current_page`, `total_pages`)
5. Duplicatas no HTML aparecem na resposta (sem deduplicação)
6. Procedimentos não-teleconsulta aparecem na resposta (sem filtro)
7. Endpoint de detalhe chama `navigator.get_appointment_detail` + parser
8. Retry funciona em caso de `SessionExpiredError`
9. Não usa `AppointmentService` — usa `get_sisreg_navigator` diretamente

## Escopo

- **Incluso:** Videofonista list + detail
- **Excluído:** Solicitante (PR posterior)
