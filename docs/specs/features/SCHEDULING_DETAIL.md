# Spec: Detalhe Completo da fichaAmbulatorial (SchedulingDetail)

## Objetivo

Extrair **todos** os campos da página `fichaAmbulatorial` do SisReg III, organizados por seção, e expor via endpoint raw do Videofonista com opções de formato JSON e PDF.

## Endpoint

```
GET /raw/videofonista/appointments/{code}
```

### Parâmetros

| Parâmetro | Tipo | Padrão | Descrição |
|-----------|------|--------|-----------|
| `code` | path | — | Código da solicitação (numérico, 1-20 dígitos) |
| `format` | query | `json` | Formato de resposta: `json` ou `pdf` |

### Respostas

- `format=json` → `SchedulingDetailResponse` (JSON)
- `format=pdf` → `application/pdf` (fichaAmbulatorial convertida via weasyprint)

## Modelo de Dados

```
SchedulingDetail
├── code, confirmation_key
├── requesting_unit: RequestingUnit
│   ├── name, cnes, solicitation_operator, videocall_operator
├── executing_unit: ExecutingUnit
│   ├── name, cnes, authorizer_operator, slot_consumed
│   ├── address, address_number, address_complement, approval_date
│   ├── phone, cep, neighborhood, municipality
│   ├── executing_professional, appointment_datetime
├── patient: PatientData
│   ├── cns, name, social_name, birth_date, sex
│   ├── mother_name, race, blood_type
│   ├── nationality, birth_country, brazil_entry_date
│   ├── address_type, street, complement, number
│   ├── neighborhood, cep
│   ├── residence_country, residence_municipality, phone
├── justification: str
├── solicitation: SolicitationData
│   ├── code, current_status
│   ├── doctor_cpf, doctor_crm, doctor_name, slot_requested
│   ├── initial_diagnosis, cid, risk
│   ├── regulatory_center
│   ├── desired_unit, desired_date, solicitation_date
└── procedure: ProcedureData
    ├── name, unified_code, internal_code
    └── preparation_title, preparation_text
```

Total: ~50 campos em 6 sub-modelos + nível superior.

## Mapeamento de Campos (Label SisReg → Campo API)

### Seção: Chave de Confirmação (tbody 1)
| Label SisReg | Campo API |
|---|---|
| Chave de Confirmação | `confirmation_key` |

### Seção: Unidade Solicitante (tbody 2)
| Label SisReg | Campo API |
|---|---|
| Unidade Solicitante | `requesting_unit.name` |
| CNES | `requesting_unit.cnes` |
| Operador Solicitação | `requesting_unit.solicitation_operator` |
| Operador Videofonista | `requesting_unit.videocall_operator` |

### Seção: Unidade Executante (tbody 3)
| Label SisReg | Campo API |
|---|---|
| Unidade Executante | `executing_unit.name` |
| CNES | `executing_unit.cnes` |
| Autorizador | `executing_unit.authorizer_operator` |
| Vaga Consumida | `executing_unit.slot_consumed` |
| Endereço | `executing_unit.address` |
| Número | `executing_unit.address_number` |
| Complemento | `executing_unit.address_complement` |
| Data Aprovação | `executing_unit.approval_date` |
| Telefone | `executing_unit.phone` |
| CEP | `executing_unit.cep` |
| Bairro | `executing_unit.neighborhood` |
| Município | `executing_unit.municipality` |
| Profissional Executante | `executing_unit.executing_professional` |
| Data/Hora Atendimento | `executing_unit.appointment_datetime` |

### Seção: Dados do Paciente (tbody 4 — ficha completa)
| Label SisReg | Campo API |
|---|---|
| CNS | `patient.cns` |
| Nome | `patient.name` |
| Nome Social | `patient.social_name` |
| Data Nascimento | `patient.birth_date` |
| Sexo | `patient.sex` |
| Nome da Mãe | `patient.mother_name` |
| Raça/Cor | `patient.race` |
| Tipo Sanguíneo | `patient.blood_type` |
| Nacionalidade | `patient.nationality` |
| País Nascimento | `patient.birth_country` |
| Data Entrada Brasil | `patient.brazil_entry_date` |
| Tipo Logradouro | `patient.address_type` |
| Logradouro | `patient.street` |
| Complemento | `patient.complement` |
| Número | `patient.number` |
| Bairro | `patient.neighborhood` |
| CEP | `patient.cep` |
| País Residência | `patient.residence_country` |
| Município Residência | `patient.residence_municipality` |
| Telefone | `patient.phone` |

### Seção: Laudo / Justificativa (tbody 6)
| Label SisReg | Campo API |
|---|---|
| Justificativa | `justification` |

### Seção: Dados da Solicitação (tbody 9 — ficha completa)
| Label SisReg | Campo API |
|---|---|
| Código | `solicitation.code` |
| Situação Atual | `solicitation.current_status` |
| CPF Médico | `solicitation.doctor_cpf` |
| CRM Médico | `solicitation.doctor_crm` |
| Nome Médico | `solicitation.doctor_name` |
| Vaga Solicitada | `solicitation.slot_requested` |
| Diagnóstico Inicial | `solicitation.initial_diagnosis` |
| CID | `solicitation.cid` |
| Risco | `solicitation.risk` |
| Central Regulação | `solicitation.regulatory_center` |
| Unidade Desejada | `solicitation.desired_unit` |
| Data Desejada | `solicitation.desired_date` |
| Data Solicitação | `solicitation.solicitation_date` |

### Seção: Procedimentos Solicitados (tbody 11)
| Label SisReg | Campo API |
|---|---|
| Procedimento | `procedure.name` |
| Código Unificado | `procedure.unified_code` |
| Código Interno | `procedure.internal_code` |
| Título Preparo | `procedure.preparation_title` |
| Texto Preparo | `procedure.preparation_text` |

## Compatibilidade

- `AppointmentDetail` (modelo antigo) permanece inalterado
- Endpoints de regulação (`/regulation/`) continuam usando `AppointmentDetail`
- Apenas o endpoint raw Videofonista detail muda para `SchedulingDetail`

## Estrutura HTML SisReg

12 tbodies em `#fichaAmbulatorial`:

| tbody | Seção | Modo |
|-------|-------|------|
| 1 | Chave de Confirmação | sempre |
| 2 | Unidade Solicitante | sempre |
| 3 | Unidade Executante | sempre |
| 4 | Dados do Paciente (completa) | ficha completa |
| 5 | Dados do Paciente (reduzida) | ficha reduzida |
| 6 | Laudo / Justificativa | sempre |
| 7 | (vazio) | — |
| 8 | Header "Dados da Solicitação" | sempre |
| 9 | Dados da Solicitação (completa) | ficha completa |
| 10 | Dados da Solicitação (reduzida) | ficha reduzida |
| 11 | Procedimentos Solicitados | sempre |
| 12 | (vazio) | — |

Parseamos sempre as tbodies da ficha completa (4, 9).

## Critérios de Aceite

1. Todos os ~50 campos são extraídos corretamente do HTML
2. Campos ausentes retornam string vazia (não None, não erro)
3. Telefone do paciente é limpo (remove "(Exibir Lista Detalhada)")
4. `format=pdf` retorna PDF válido com `application/pdf`
5. Testes unitários cobrem todos os campos
6. Endpoints de regulação não são afetados (backward compatible)
