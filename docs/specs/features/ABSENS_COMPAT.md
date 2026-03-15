# Endpoints de Compatibilidade Absens — Drop-in Replacement

## Contexto

O `ptm-regulation-service` (.NET 9) consome dados de agendamentos de teleconsulta da API externa Absens (`workflow.quoti.cloud`). Este recurso permite que o `regula-hub` (FastAPI) forneça os **mesmos 3 endpoints** com o **mesmo contrato JSON**, permitindo trocar apenas as URLs de config no regulation-service sem alteração de código.

## Endpoints

### 1. `GET /api/compat/absens/agendamentos?date=YYYY-MM-DD`

Retorna `AppointmentDTO[]` (listagem de agendamentos).

| Campo JSON (camelCase) | Tipo | Nullable | Fonte |
|------------------------|------|----------|-------|
| `cod` | string | Não | `AppointmentListing.code` |
| `patientBirthday` | string | Não | Enriched from SisReg detail (`patient_birth_date`) |
| `patientMotherName` | string | Não | CadWeb `mother_name` (via Consulta CNS) ou `""` se indisponível |
| `departmentExecute` | string | Não | `AppointmentListing.dept_execute` |
| `departmentSolicitation` | string | Não | `AppointmentListing.dept_solicitation` |
| `procedure` | string | Não | `AppointmentListing.procedure` |
| `statusSisreg` | string | Sim | `AppointmentListing.status` |

### 2. `GET /api/compat/absens/agendamentos?codigo=COD`

Retorna `DetailsAppointmentDTO` (detalhes de um agendamento).

| Campo JSON (camelCase) | Tipo | Nullable | Fonte |
|------------------------|------|----------|-------|
| `id` | string | Sim | `null` |
| `cod` | string | Não | `AppointmentDetail.sol_code or code` |
| `confirmationKey` | string | Não | `AppointmentDetail.confirmation_key or ""` |
| `patient` | string | Não | `AppointmentDetail.patient_name or ""` |
| `patientCPF` | string | Sim | CadWeb CPF (via Consulta CNS) ou `null` se indisponível |
| `cns` | string | Não | `AppointmentDetail.patient_cns or ""` |
| `patientPhones` | PhoneDto[] | Sim | derivado de `best_phone` |
| `departmentSolicitation` | string | Não | `AppointmentDetail.req_unit_name or ""` |
| `departmentExecute` | string | Não | `AppointmentDetail.department or ""` |
| `appointmentDateTimestamp` | DateTime | Sim | `null` |
| `appointmentDate` | string | Não | construído no formato `●` |
| `statusSisreg` | string | Não | `AppointmentDetail.sol_status or ""` |
| `doctorExecute` | string | Não | `AppointmentDetail.doctor_name or ""` |
| `status` | string | Não | `""` |
| `bestPhone` | PhoneDto | Sim | CadWeb CELULAR (preferido) ou `AppointmentDetail.best_phone` (fallback) |
| `departmentSolicitationInfos` | DeptInfoDto | Sim | construído de `req_unit_cnes` e `req_unit_name` (null se ambos ausentes) |

### 3. `GET /api/compat/absens/cancelamentos?date=YYYY-MM-DD`

Retorna `501 Not Implemented`. Seguro — o regulation-service captura a exception e continua.

## Autenticação

Header `Authorization` com API key. Isolado dos endpoints admin (`X-API-Key`).

## Formato `appointmentDate`

Formato: `"DIA ● dd/MM/yyyy ● HHhMMmin"` (3 partes separadas por `●`).

- Se `appointment_date` já contém `●`, passthrough
- Se é `dd/MM/yyyy`, construir com dia da semana pt-BR e `00h00min`
- Se é `dd/MM/yyyy HH:mm`, construir com dia da semana pt-BR e hora

## Config do regulation-service

```json
"AbsensApiConfig": {
    "BaseUrl": "http://<regula-hub-host>:8000/",
    "ApiKey": "<regula-hub-api-key>",
    "SchedulingEndpoint": "api/compat/absens/agendamentos",
    "CancellationsEndpoint": "api/compat/absens/cancelamentos",
    "MaxRetries": 3,
    "MaxConcurrency": 20,
    "DaysBack": 3
}
```

## Estratégia de Enrichment (Detail + CadWeb)

O listing do SisReg não retorna `patientBirthday`, `patientMotherName` ou `patientCPF`. Para enriquecer esses campos, o serviço:

1. **Coleta os codes** de todos os agendamentos retornados pelo listing
2. **Distribui via round-robin** entre as credentials disponíveis (VIDEOFONISTA)
3. **Busca details em paralelo** usando `asyncio.Semaphore(5)` para limitar sessões SisReg simultâneas
4. **Cada credential** abre 1 sessão SisReg (1 login, N detail + CadWeb calls, 1 logout)
5. **Para cada code**: busca detail (fichaAmbulatorial) + CadWeb lookup (Consulta CNS pelo patient_cns)
6. **Cache CadWeb por CNS**: mesmo paciente em múltiplos agendamentos → 1 query CadWeb
7. **Fallback gracioso**:
   - Falha de login → todos os codes do batch sem enrichment
   - Falha de detail individual → aquele code sem enrichment
   - Falha de CadWeb → detail ainda usado (CPF=null, mother_name="", phone da fichaAmbulatorial)

Veja [CADWEB_INTEGRATION.md](CADWEB_INTEGRATION.md) para detalhes da integração CadWeb.

## Critérios de Aceitação

- [ ] Endpoints retornam JSON com campos camelCase idênticos ao contrato Absens
- [ ] Campos `required string` nunca retornam `null` (sempre `""`)
- [ ] Autenticação via header `Authorization` isolada dos endpoints admin
- [ ] Formato `appointmentDate` no padrão `●` esperado pelo regulation-service
- [ ] Endpoint de cancelamentos retorna 501
- [ ] Rate limiting aplicado (200/minute)
- [ ] Testes unitários cobrindo schemas, auth, service e routes

## Exceções Documentadas aos Guardrails

### E1. Sem paginação (`skip`/`limit`) — BACKEND_GUARDRAILS §3.2

O regulation-service (.NET) chama `GET /agendamentos?date=YYYY-MM-DD` e espera a lista completa. Não envia `skip`/`limit`. Adicionar esses params não quebraria (seriam opcionais), mas o consumidor nunca os usaria.

### E2. `logging` stdlib em vez de `structlog` — BACKEND_GUARDRAILS §3.7

O `sisreg_routes.py` existente (referência direta deste código) também usa `logging` stdlib. Migrar só os compat modules criaria inconsistência. Resolver junto num `chore: migrate to structlog` futuro.

### E3. `SISREG_BASE_URL` hardcoded — CONSTITUTION §8

O `sisreg_routes.py` original tem o mesmo hardcode. Corrigir isoladamente cria inconsistência. Resolver junto num chore futuro.
