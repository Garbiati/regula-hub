# Constituição do Projeto

Princípios fundamentais que governam todo o desenvolvimento deste serviço.
Nenhuma implementação pode violar estas regras, independentemente do contexto.

## Identidade

- **Nome:** regula-hub
- **Tipo:** WebAPI REST
- **Domínio:** Extração de dados de agendamentos de teleconsulta do SisReg III
- **Escopo inicial:** Estado do Amazonas (AM)

## Princípios Invioláveis

### 1. Proteção de Dados (LGPD)

- NUNCA logar, armazenar em cache ou expor dados de pacientes (nome, CPF, CNS, telefone) fora do banco de dados da aplicação. Dados de agendamentos podem ser persistidos no PostgreSQL para uso offline quando o SisReg estiver indisponível, desde que: (1) controlado por opt-in explícito do operador, (2) dados protegidos pelas mesmas regras de acesso da API (X-API-Key), (3) PII nunca exposto em logs
- NUNCA persistir credenciais do SisReg em código, logs ou respostas de API
- Credenciais devem vir exclusivamente de variáveis de ambiente ou secret manager
- Dados sensíveis em logs devem ser mascarados (ex: CPF `***.***.***-XX`)

### 2. Spec First - Especificação Antes de Código

- NUNCA implementar uma funcionalidade sem uma spec aprovada em `docs/specs/`
- Cada feature deve ter seu arquivo de spec antes de qualquer linha de código
- A spec é o contrato: se o código diverge da spec, o código está errado
- Alterações de comportamento exigem atualização da spec ANTES do código

### 3. Sem Regressão

- NUNCA alterar uma funcionalidade existente sem antes:
  1. Ler a spec correspondente
  2. Ler os testes existentes
  3. Garantir que os testes existentes continuam passando
- Cada bug fix deve incluir um teste que reproduz o bug
- Cada feature deve incluir testes que validam os critérios de aceite da spec

### 4. Sem Alucinação

- NUNCA inventar endpoints, campos ou comportamentos do SisReg que não foram verificados
- NUNCA assumir a estrutura de uma resposta HTML do SisReg sem evidência
- Quando a estrutura do HTML for desconhecida, criar uma task de investigação antes de implementar
- Mapear XPaths e seletores a partir de evidências reais (curl, HTML salvo, screenshots)

### 5. Escopo Controlado

- NUNCA adicionar funcionalidades não solicitadas (no gold plating)
- NUNCA refatorar código adjacente que não faz parte da task atual
- NUNCA criar abstrações "para o futuro" - resolver o problema atual com a solução mais simples
- Se uma mudança afeta mais de 3 arquivos, parar e validar o escopo

## Fluxo de Trabalho Obrigatório

```text
1. Spec     -> Definir O QUE e POR QUE (docs/specs/features/)
2. Design   -> Definir COMO (dentro da spec)
3. Tasks    -> Quebrar em tarefas atômicas e testáveis
4. Implement -> Código + testes (uma task por vez)
5. Verify   -> Testes passando + spec satisfeita
```

## Hierarquia de Documentos

Quando houver conflito entre documentos, a prioridade é:

1. `CONSTITUTION.md` (este arquivo) - Princípios invioláveis
2. `BUSINESS_RULES.md` - Regras de negócio do domínio
3. `TECH_SPEC.md` - Decisões técnicas e arquiteturais
4. `features/*.md` - Specs de funcionalidades individuais
5. `CLAUDE.md` - Instruções operacionais para o agente

### 6. Política de Idioma (Imutável)

Todo artefato de **código** é em **inglês**. Toda **documentação** é em **português (pt-BR)**.

**Inglês (obrigatório):**

- Código-fonte (variáveis, funções, classes, interfaces, tipos)
- Comentários no código
- Mensagens de commit
- Nomes de branches (ex: `feat/list-appointments`, `fix/session-timeout`)
- Nomes de features e tasks
- Tags e releases
- Títulos e descrições de Pull Requests
- Mensagens de log da aplicação
- Nomes de arquivos de código-fonte

**Português (pt-BR) (obrigatório):**

- Documentação (`docs/`, `doc/`, `readme.md`)
- Specs (`docs/specs/`)
- Regras de negócio
- Comentários em arquivos de documentação

**Exceção — termos do domínio SisReg:**

Termos vindos diretamente do SisReg são mantidos em português como o sistema os retorna (ex: `Videofonista`, `Solicitante`, `fichaAmbulatorial`, nomes de procedimentos). Estes termos NÃO devem ser traduzidos no código — são nomes próprios do domínio.

### 7. Observabilidade Obrigatória

- NUNCA implantar um endpoint sem request logging estruturado
- NUNCA processar um request sem X-Request-ID (gerar se ausente)
- NUNCA logar exceções sem contexto (method, path, remote_addr)
- Todo health check DEVE validar TODAS as dependências críticas

### 8. Segurança de Configuração (Fail-Fast)

- NUNCA aceitar config semântica sem validação no startup
  - Chaves Fernet DEVEM ser testadas com `Fernet(key)` durante init
  - URLs DEVEM ser validadas com `AnyHttpUrl` ou `urlparse`
  - Timeouts DEVEM ser positivos
- NUNCA usar wildcard em CORS headers
- NUNCA ter fallback silencioso para credenciais/chaves (falhar alto)

### 9. Integridade de Dados

- NUNCA fazer query dentro de loop (N+1) — usar IN clause ou JOIN
- NUNCA fazer commit fora de transação atômica (`async with db.begin()`)
- NUNCA expor endpoint de listagem sem paginação
- NUNCA aceitar input string sem `min_length`/`max_length`

### 10. Proteção Ativa

- NUNCA registrar mecanismo de proteção (rate limit, auth, CORS) sem ativá-lo
- Se o código tem `slowapi`, TODO endpoint deve ter `@limiter.limit()`
- Se o código tem `verify_api_key`, TODA rota sensível deve usá-lo como dependência
