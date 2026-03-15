# Listagem de Agendamentos

## Objetivo

Expor via API REST a listagem de agendamentos de teleconsulta do SisReg III, filtrados por período e código de procedimento.

## Endpoint

```text
GET /appointments?start_date={dd/MM/yyyy}&end_date={dd/MM/yyyy}&procedure_codes={code1,code2,...}
```

## Parâmetros de Entrada

| Parâmetro        | Tipo       | Obrigatório | Descrição                               |
| ---------------- | ---------- | ----------- | --------------------------------------- |
| start_date       | string     | Sim         | Data inicial (dd/MM/yyyy)               |
| end_date         | string     | Sim         | Data final (dd/MM/yyyy)                 |
| procedure_codes  | list[str]  | Não         | Códigos internos de procedimento SisReg |

## Resposta

```json
{
  "appointments": [
    {
      "code": "1234567890",
      "request_date": "01/03/2026",
      "risk": 0,
      "patient": "JOAO DA SILVA",
      "age": "45",
      "procedure": "TELECONSULTA EM CARDIOLOGIA",
      "cid": "I10",
      "department_solicitation": "UBS CENTRO",
      "department_execute": "HOSPITAL REGIONAL",
      "status_sisreg": "AGE/PEN/EXEC"
    }
  ],
  "total": 1
}
```

## Fluxo Interno

1. Autenticar no SisReg III (POST `/` com SHA-256)
2. Para cada `procedure_code` (ou todos, se não informado):
   a. Aplicar filtros via `GET /cgi-bin/gerenciador_solicitacao` com `etapa=LISTAR_SOLICITACOES`
   b. Parsear tabela de resultados (`.table_listagem tbody tr`)
   c. Se houver paginação, iterar todas as páginas
3. Deduplicar agendamentos por código
4. Logout

## Regras de Negócio

- Filtro de situação fixo: `9` (solicitação / agendada / fila de espera)
- Registros por página: `0` (todos)
- Tipo de período: `A` (agendamento)
- Perfil Videofonista: visão estadual, itera todos os códigos de procedimento
- Deduplicação: mesmo código de agendamento não aparece duas vezes

## Tratamento de Erros

| Cenário                  | HTTP Status | Descrição                      |
| ------------------------ | ----------- | ------------------------------ |
| Login falhou             | 401         | Credenciais inválidas          |
| Sessão expirada          | 503         | Após 3 tentativas de reconexão |
| Nenhum registro          | 200         | Lista vazia, `total: 0`        |
| SisReg indisponível      | 502         | Erro de conexão HTTP           |
| Perfil não implementado  | 501         | ProfileType não suportado      |

## Critérios de Aceite

- [ ] Retorna lista de agendamentos para um período válido
- [ ] Filtra por código de procedimento quando informado
- [ ] Itera todas as páginas de resultados
- [ ] Deduplicar agendamentos por código
- [ ] Retorna lista vazia (não erro) quando não há resultados
- [ ] Re-autentica automaticamente em caso de sessão expirada
- [ ] Não loga dados de pacientes em plain text
