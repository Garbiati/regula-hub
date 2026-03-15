# Detalhes do Agendamento

## Objetivo

Expor via API REST os detalhes completos de um agendamento específico do SisReg III, incluindo dados do paciente, médico, unidade e telefone de contato.

## Endpoint

```text
GET /appointments/{code}
```

## Parâmetros de Entrada

| Parâmetro | Tipo   | Obrigatório | Descrição                   |
| --------- | ------ | ----------- | --------------------------- |
| code      | string | Sim         | Código do agendamento       |

## Resposta

```json
{
  "detail": {
    "code": "1234567890",
    "confirmation_key": "CONF-KEY-12345",
    "cns": "123456789012345",
    "appointment_date": "15/03/2026",
    "doctor_solicitation": "DR. MEDICO",
    "doctor_crm": "CRM-12345",
    "doctor_solicitation_cpf": "***.***.***-00",
    "priority": "ALTA",
    "regulatory_center": "CENTRAL DE REGULACAO AM",
    "cnes": "2018756",
    "department": "HOSPITAL REGIONAL DE MANAUS",
    "videocall_operator": "OPERADOR VIDEOCALL",
    "solicitation_operator": "OPERADOR SOLICITACAO",
    "observations": "Paciente com historico de HAS",
    "best_phone": {
      "ddd": "92",
      "number": "98765-4321",
      "phone_type": "mobile",
      "raw": "(92) 98765-4321"
    }
  }
}
```

## Fluxo Interno

1. Autenticar no SisReg III (se não autenticado)
2. `GET /cgi-bin/gerenciador_solicitacao?etapa=VISUALIZAR_FICHA&co_solicitacao={code}`
3. Parsear tabela `#fichaAmbulatorial` usando selectors centralizados
4. Extrair telefone com fallback (primary: `tbody[4]/tr[16]/td`, fallback: `tbody[4]/tr[12]/td`)
5. Classificar telefone (mobile/landline)
6. Retornar `AppointmentDetail`

## Campos Extraídos

| Campo                  | Selector CSS (relativo a #fichaAmbulatorial)              |
| ---------------------- | --------------------------------------------------------- |
| confirmation_key       | `tbody:nth-child(1) tr:nth-child(2) td`                   |
| cns                    | `tbody:nth-child(4) tr:nth-child(2) td font`              |
| appointment_date       | `tbody:nth-child(3) tr:nth-child(9) td:nth-child(2) font b` |
| doctor_solicitation    | `tbody:nth-child(9) tr:nth-child(4) td:nth-child(3)`      |
| doctor_crm             | `tbody:nth-child(9) tr:nth-child(4) td:nth-child(2)`      |
| doctor_solicitation_cpf| `tbody:nth-child(9) tr:nth-child(4) td:nth-child(1)`      |
| priority               | `tbody:nth-child(9) tr:nth-child(6) td:nth-child(3) b font` |
| regulatory_center      | `tbody:nth-child(9) tr:nth-child(8) td`                   |
| cnes                   | `tbody:nth-child(2) tr:nth-child(3) td:nth-child(2)`      |
| department             | `tbody:nth-child(9) tr:nth-child(10) td:nth-child(2)`     |
| videocall_operator     | `tbody:nth-child(2) tr:nth-child(3) td:nth-child(4)`      |
| solicitation_operator  | `tbody:nth-child(2) tr:nth-child(3) td:nth-child(3)`      |
| observations           | `tbody:nth-child(11) tr:nth-child(5) td`                  |
| phone (primary)        | `tbody:nth-child(4) tr:nth-child(16) td`                  |
| phone (fallback)       | `tbody:nth-child(4) tr:nth-child(12) td`                  |

## Regras de Extração de Telefone (BestPhone)

1. Tentar extrair do local primário
2. Se não encontrar, tentar fallback
3. Remover texto `(Exibir Lista Detalhada)`
4. Extrair DDD com regex: `\((\d{2})\)`
5. Extrair número com regex: `(\d{4,5})-(\d{4})`
6. Classificar tipo:
   - Mobile: `^\(\d{2}\)\s*[6-9]\d{4}-\d{4}$`
   - Landline: todos os outros

## Tratamento de Erros

| Cenário                     | HTTP Status | Descrição                         |
| --------------------------- | ----------- | --------------------------------- |
| Login falhou                | 401         | Credenciais inválidas             |
| Sessão expirada             | 503         | Após 3 tentativas de reconexão    |
| Ficha não encontrada        | 200         | Retorna detail com campos vazios  |
| Telefone não encontrado     | 200         | `best_phone: null`                |
| Perfil não implementado     | 501         | ProfileType não suportado         |

## Critérios de Aceite

- [ ] Retorna todos os campos documentados para um agendamento válido
- [ ] Extrai telefone do local primário
- [ ] Faz fallback para local secundário se primário vazio
- [ ] Classifica corretamente telefone mobile vs landline
- [ ] Remove texto "(Exibir Lista Detalhada)" do telefone
- [ ] Retorna `best_phone: null` se nenhum telefone encontrado
- [ ] Re-autentica automaticamente em caso de sessão expirada
- [ ] Não loga CPF, CNS ou telefone em plain text nos logs
