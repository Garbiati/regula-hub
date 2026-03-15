# Regras de Negócio

Regras do domínio SisReg que o agente de IA DEVE conhecer antes de implementar qualquer funcionalidade.

## Contexto do Domínio

O SisReg III é o sistema de regulação do SUS. Ele **não possui API pública**. Todos os dados são acessados via interface web (HTML renderizado no servidor com CGI). Este serviço existe para expor esses dados via API REST.

## Perfis de Acesso

### Videofonista (perfil principal)

- Vinculado a uma unidade de saúde, mas tem **visão estadual**
- Pode visualizar agendamentos de **todos os municípios** do estado
- Acesso ao menu de agendamentos via `li[3]` da barra de menu
- Este é o perfil usado para a **listagem geral** de teleconsultas
- Usado quando `perfil.descricao == "VIDEOFONISTA"`

### Solicitante/Executante

- Vinculado a uma unidade de saúde específica
- Visão **limitada à sua unidade**
- Acesso ao menu via `li[5]` da barra de menu, com submenu `li[5] > ul > li[2]`
- Usado para **listagem e exportação** de agendamentos da unidade
- **LIMITAÇÃO CRÍTICA:** Pesquisa por código de solicitação só retorna resultados se o agendamento foi **emitido pela unidade do operador**. Agendamentos de outras unidades são invisíveis neste perfil.

### Regra de Visibilidade por Perfil

```text
┌──────────────────────────────────────────────────────────────────┐
│ VIDEOFONISTA (visão estadual)                                    │
│ → Pode buscar QUALQUER agendamento por código, independente     │
│   da unidade de origem                                           │
│ → Usado para: busca de detalhes por código                      │
├──────────────────────────────────────────────────────────────────┤
│ SOLICITANTE/EXECUTANTE (visão por unidade)                       │
│ → Só retorna agendamentos da SUA unidade                        │
│ → Pesquisa por código NÃO retorna agendamentos de outras        │
│   unidades (retorna "nenhum registro encontrado")               │
│ → Usado para: listagem em massa e exportação CSV/TXT por unidade│
└──────────────────────────────────────────────────────────────────┘
```

**Consequência para encadeamento:** Para obter detalhes completos de todos os agendamentos, é necessário usar **ambos os perfis**:
1. **Solicitante** (por unidade) → exportar CSV com todos os agendamentos
2. **Videofonista** (estadual) → buscar detalhes por código de qualquer agendamento

### Regra de seleção de perfil

```text
SE perfil == "VIDEOFONISTA":
  -> Menu de agendamentos em li[3]
  -> Filtrar por especialidade (código de procedimento)
SENÃO:
  -> Menu em li[5], submenu li[5] > ul > li[2]
  -> Sem filtro por especialidade
```

## Operadores e Unidades

- Cada **operador** tem login/senha próprios vinculados ao SisReg
- Um operador pertence a uma **unidade** (estabelecimento de saúde)
- Múltiplos operadores podem pertencer à mesma unidade
- Ao iterar operadores, **pular operadores da mesma unidade já processada**
- Operadores com login inválido devem ser registrados (log) e pulados

### Restrição de Estado e Sistema (RegulaHub)

- Todos os operadores/videofonistas selecionados em uma sessão devem pertencer ao **mesmo estado** (UF)
- Todos devem pertencer ao **mesmo sistema** (e.g., SISREG)
- Enforcement: UI — seletor de estado filtra usuários, impedindo seleção cruzada
- Validação backend: pendente (será implementada na API)
- Motivação: cada instância do SisReg é estadual; misturar estados causaria dados inconsistentes

## Agendamentos

### Campos da Listagem (tabela de resultados)

| Coluna | Campo               | Descrição                                  |
|--------|---------------------|--------------------------------------------|
| 0      | Cod                 | Código do agendamento (numérico)           |
| 1      | DataSolicitacao     | Data da solicitação (dd/MM/yyyy)           |
| 2      | Risco               | Nível de risco (numérico, default 0)       |
| 3      | Patient             | Nome do paciente                           |
| 6      | Idade               | Idade do paciente                          |
| 7      | Procedure           | Nome do procedimento                       |
| 8      | CID                 | Código CID da condição                     |
| 9      | DepartmentSolicitation | Unidade solicitante                     |
| 10     | DepartmentExecute   | Unidade executante                         |
| 12     | StatusSisreg        | Status no SisReg (ex: "AGE/PEN/EXEC")     |

### Campos dos Detalhes (página do agendamento)

| Campo                    | Origem                              | Observação                      |
|--------------------------|-------------------------------------|---------------------------------|
| ConfirmationKey          | Chave de confirmação do agendamento | Gerada pelo sistema             |
| CNS                      | Cartão Nacional de Saúde            | Identificador do paciente       |
| AppointmentDate          | Data do agendamento                 |                                 |
| DoctorSolicitation       | Médico solicitante (nome)           |                                 |
| DoctorCRM                | CRM do médico                       |                                 |
| DoctorSolicitationCPF    | CPF do médico solicitante           | Dado sensível - mascarar em log |
| Priority                 | Prioridade do agendamento           |                                 |
| RegulatoryCenter         | Central de regulação                |                                 |
| CNES                     | Código CNES da unidade              |                                 |
| Department               | Unidade/departamento                |                                 |
| VideocallOperator        | Operador da videochamada            |                                 |
| SolicitationOperator     | Operador da solicitação             |                                 |
| Observations             | Observações do agendamento          | Pode não existir                |
| BestPhone                | Melhor telefone de contato          | Dado sensível                   |

### Regras do Telefone (BestPhone)

```text
1. Tentar extrair de tbody[4]/tr[16]/td
2. Se não encontrar, fallback para tbody[4]/tr[12]/td
3. Remover texto "(Exibir Lista Detalhada)"
4. Extrair DDD com regex: \((\d{2})\)
5. Extrair número com regex: \((\d{4,5})-(\d{4})
6. Classificar tipo:
   - Mobile: regex ^\(\d{2}\)\s*[6-9]\d{4}-\d{4}$
   - Landline: todos os outros
```

### Status do Agendamento

- `"AGE/PEN/EXEC"` = Agendado (status válido para processamento)
- Filtro de situação no SisReg: valor `9` = solicitação / agendada / fila de espera

## Filtros de Busca

### Parâmetros obrigatórios

| Parâmetro        | Valor                        | Descrição                     |
|------------------|------------------------------|-------------------------------|
| dataInicial      | dd/MM/yyyy                   | Data inicial do período       |
| dataFinal        | dd/MM/yyyy                   | Data final do período         |
| cmb_situacao     | `9`                          | Solicitação / agendada / fila de espera |
| registros        | `0`                          | Todos os registros (sem paginação do filtro) |

### Parâmetro condicional

| Parâmetro        | Quando usar                  | Valor                         |
|------------------|------------------------------|-------------------------------|
| especialidade    | Perfil VIDEOFONISTA          | Código interno do procedimento (ex: `739135`) |

## Procedimentos de Teleconsulta

Os códigos internos do SisReg para teleconsultas estão documentados em [doc/procedures.md](../../doc/procedures.md).

Regras importantes:
- Um mesmo código pode mapear para mais de uma especialidade (ex: 739140 = Endocrinologia e Endocrinologia Pediátrica)
- Um mesmo código pode ter variantes com restrição de faixa etária (ex: 739144 = Neurologia Geral e Neurologia Geral a partir de 12 anos)
- A listagem deve iterar por **todos os códigos** de procedimento ao usar o perfil Videofonista

## Paginação

- A tabela de resultados pode ter múltiplas páginas
- O número total de páginas é extraído do texto da paginação via regex `\d+`
- Para navegar: preencher o campo de página com o número e pressionar Enter
- Aguardar o indicador `#status_page` com `style="display: none;"` antes de parsear

## Sessão e Estabilidade

- Sessões do SisReg podem expirar a qualquer momento
- Detectar sessão expirada: elemento em `html/body/table/tbody/tr[9]/td/center/i/span`
- Se detectada sessão expirada: fazer logout, re-autenticar e retomar do ponto de parada
- Ao clicar em um agendamento e falhar (página de "avisos"): voltar ao menu, reaplicar filtros e retomar pelo índice

## O Que NUNCA Fazer

- NUNCA executar ações de escrita no SisReg (autorizar, cancelar, agendar) - este serviço é SOMENTE LEITURA
- NUNCA armazenar dados de pacientes em cache persistente fora do banco de dados da aplicação. Dados de agendamentos podem ser persistidos no PostgreSQL para uso offline quando o SisReg estiver indisponível, desde que: (1) controlado por opt-in explícito do operador, (2) dados protegidos pelas mesmas regras de acesso da API (X-API-Key), (3) PII nunca exposto em logs
- NUNCA logar dados completos de CPF, CNS ou telefone
- NUNCA fazer mais de uma sessão simultânea por operador (risco de bloqueio)
- NUNCA ignorar sessão expirada - detectar e re-autenticar
- NUNCA assumir que a estrutura HTML do SisReg é estável - ela pode mudar sem aviso
