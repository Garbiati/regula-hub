# Spec: External API Clients

## Contexto

O pipeline de integração precisa se comunicar com dois serviços internos do PTM:
- **ptm-auth-server** — para registrar novos pacientes
- **ptm-core-api** — para buscar/atualizar pacientes, listar médicos, e criar lembretes

## Clientes

### AuthClient (ptm-auth-server)
- `register_patient(dto) -> UUID` — POST /api/patients, retorna patient_id
- Autenticação via API key no header

### CoreApiClient (ptm-core-api)
- `get_patient_by_cpf(cpf) -> PatientDTO | None` — GET /api/patients?cpf=...
- `update_patient(patient_id, dto)` — PUT /api/patients/{id}
- `get_doctors() -> list[DoctorDTO]` — GET /api/doctors (cache 30min)
- `get_reminder_by_external_id(external_id) -> UUID | None` — GET /api/reminders?externalId=...
- `create_reminder(dto) -> UUID` — POST /api/reminders

## Configuração
- `CORE_API_BASE_URL`, `CORE_API_API_KEY`, `CORE_API_TIMEOUT_SECONDS`
- `AUTH_API_BASE_URL`, `AUTH_API_API_KEY`, `AUTH_API_TIMEOUT_SECONDS`

## Tecnologia
- HTTPX async client
- Retry com Tenacity (3 tentativas, exponential backoff)
- Testes com `respx`

## Critérios de aceitação
1. Clientes usam HTTPX async
2. Testes com respx mockando as APIs externas
3. Configuração via Pydantic Settings
