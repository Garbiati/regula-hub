# Controller de Integração para Regulation Service

## Objetivo

Fornecer endpoints compatíveis com a API do Absens (`workflow.quoti.cloud`) para que o `ptm-regulation-service` (.NET) possa migrar do Absens para o scrapper sem alterações de código. O scrapper deve ser um **drop-in replacement**: mesma estrutura JSON, mesmos nomes de campo em camelCase, mesmos tipos.

## Contexto

O `AbsensApiClient.cs` no regulation-service faz 3 chamadas:

| Chamada | Path Absens | Resposta |
|---------|-------------|----------|
| `GetSchedulingAsync(date)` | `agendamentos?date=YYYY-MM-DD` | `AppointmentDTO[]` |
| `GetSchedulingDetailsAsync(cod)` | `agendamentos?codigo=COD` | `DetailsAppointmentDTO` |
| `GetCanceledAppointmentCodesAsync(date)` | `cancelamentos?date=YYYY-MM-DD` | `[{codAppointment}]` |

## Endpoints

### Listagem de Agendamentos

```text
GET /regulation/appointments?date=YYYY-MM-DD
```

**Parâmetros:**

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| date | string | Sim* | Data no formato ISO (YYYY-MM-DD) |
| codigo | string | Sim* | Código do agendamento |

*Mutuamente exclusivos: enviar `date` OU `codigo`, nunca ambos.

**Estratégia de busca:**

O endpoint itera sobre todos os códigos de procedimento de teleconsulta definidos em `src/regulahub/procedures.py` (`DEFAULT_PROCEDURE_CODES`, 19 códigos). Para cada código, faz uma requisição filtrada ao SisReg via `co_pa_interno`, que retorna muito mais rápido do que uma requisição sem filtro. Os resultados são consolidados e deduplicados por código de agendamento.

Diferença do Absens: o Absens retornava TODOS os agendamentos sem filtro. O scrapper retorna apenas teleconsultas, mas o regulation-service já consome apenas teleconsultas, então a compatibilidade é mantida.

**Resposta com `date`** — JSON array:

```json
[
  {
    "cod": "1234567890",
    "patientBirthday": "",
    "patientMotherName": "",
    "departmentExecute": "POLICLINICA CODAJAS",
    "departmentSolicitation": "UBS EXEMPLO",
    "procedure": "TELECONSULTA EM CARDIOLOGIA",
    "statusSisreg": "AGENDADO"
  }
]
```

**Resposta com `codigo`** — JSON object:

```json
{
  "id": null,
  "cod": "1234567890",
  "confirmationKey": "ABC123",
  "patient": "",
  "patientCPF": null,
  "cns": "123456789012345",
  "patientPhones": [{"ddd": "92", "number": "98765-4321", "phoneType": "mobile"}],
  "departmentSolicitation": "",
  "departmentExecute": "",
  "appointmentDateTimestamp": "1709640000",
  "appointmentDate": "05/03/2026",
  "statusSisreg": "",
  "doctorExecute": "",
  "status": "",
  "bestPhone": {"ddd": "92", "number": "98765-4321", "phoneType": "mobile"},
  "departmentSolicitationInfos": null
}
```

### Cancelamentos

```text
GET /regulation/cancellations?date=YYYY-MM-DD
```

Retorna **501 Not Implemented**. O Absens rastreava cancelamentos por diff de estado ao longo do tempo — funcionalidade não replicável via scraping.

## Regras de Mapeamento

### Campos da Listagem

| Campo DTO .NET | Tipo .NET | Fonte no Scrapper | Fase |
|---|---|---|---|
| `cod` | `required string` | `Appointment.code` | 1 |
| `procedure` | `required string` | `Appointment.procedure` | 1 |
| `departmentExecute` | `required string` | `Appointment.department_execute` | 1 |
| `departmentSolicitation` | `required string` | `Appointment.department_solicitation` | 1 |
| `statusSisreg` | `string?` | `Appointment.status_sisreg` | 1 |
| `patientBirthday` | `required string` | `""` (fase 2: fichaAmbulatorial) | 2 |
| `patientMotherName` | `required string` | `""` (fase 2: fichaAmbulatorial) | 2 |

### Campos do Detalhe

| Campo DTO .NET | Tipo .NET | Fonte no Scrapper | Fase |
|---|---|---|---|
| `cod` | `required string` | `AppointmentDetail.code` | 1 |
| `confirmationKey` | `required string` | `AppointmentDetail.confirmation_key` | 1 |
| `patient` | `required string` | `""` (vem do listing no regulation-service) | 1 |
| `cns` | `required string` | `AppointmentDetail.cns` | 1 |
| `appointmentDate` | `required string` | `AppointmentDetail.appointment_date` | 1 |
| `bestPhone` | `PhoneDTO?` | `AppointmentDetail.best_phone` | 1 |
| `patientPhones` | `PhoneDTO[]?` | Derivado de `best_phone` | 1 |
| `appointmentDateTimestamp` | `string?` | Computado de `appointment_date` | 1 |
| `statusSisreg` | `required string` | `""` (vem do listing no regulation-service) | 1 |
| `departmentSolicitation` | `required string` | `""` (vem do listing) | 1 |
| `departmentExecute` | `required string` | `""` (vem do listing) | 1 |
| `doctorExecute` | `required string` | `""` (fase 2) | 2 |
| `status` | `required string` | `""` (não existe no SisReg) | 1 |
| `id` | `string?` | `null` (ID interno Absens) | N/A |
| `patientCPF` | `string?` | `null` (fase 2) | 2 |
| `departmentSolicitationInfos` | `DeptInfoDTO?` | `null` (fase 2) | 2 |

### Regra Crítica: campos `required` no .NET

Campos marcados como `required string` no DTO .NET devem retornar `""` (string vazia), **NUNCA** `null`. `System.Text.Json` lança exception ao desserializar `null` em `required string`.

## Critérios de Aceite

1. `GET /regulation/appointments?date=2026-03-05` retorna JSON array com campos camelCase
2. `GET /regulation/appointments?codigo=123456` retorna JSON object com campos camelCase
3. `GET /regulation/cancellations?date=2026-03-05` retorna 501
4. Enviar `date` e `codigo` simultaneamente retorna 422
5. Todos os campos `required` no .NET retornam string (nunca `null`)
6. Serialização usa camelCase (aliases Pydantic)
7. Testes unitários para schemas e mappers
8. Todos os testes existentes continuam passando
