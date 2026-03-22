# Guia de Contribuicao

Obrigado pelo interesse em contribuir com o **RegulaHub**. Este documento descreve as regras do repositorio, o fluxo de trabalho e como participar do projeto.

---

## Indice

1. [Governanca](#governanca)
2. [Estrategia de Branches](#estrategia-de-branches)
3. [Protecao de Branches](#protecao-de-branches)
4. [Fluxo de Trabalho](#fluxo-de-trabalho)
5. [Convencoes de Commit](#convencoes-de-commit)
6. [Pull Requests](#pull-requests)
7. [Code Review](#code-review)
8. [Labels](#labels)
9. [Ambiente de Desenvolvimento](#ambiente-de-desenvolvimento)
10. [Politica de Idioma](#politica-de-idioma)
11. [Seguranca e LGPD](#seguranca-e-lgpd)
12. [Niveis de Permissao](#niveis-de-permissao)

---

## Governanca

O repositorio e mantido por **Alessandro Garbiati** ([@Garbiati](https://github.com/Garbiati)), unico administrador e code owner. Todas as decisoes finais sobre merge, arquitetura e roadmap passam por ele.

| Papel | Responsabilidades | Quem |
|-------|-------------------|------|
| **Admin** | Aprovar PRs, merge em branches protegidas, gerenciar rulesets | @Garbiati |
| **Collaborator** | Abrir PRs, fazer code review (sem poder de merge) | Colaboradores convidados |
| **Contributor** | Abrir issues, propor PRs via fork | Qualquer pessoa |

> **Nota:** No momento, somente o administrador pode aprovar e fazer merge de PRs. Veja [Niveis de Permissao](#niveis-de-permissao) para o plano futuro de delegacao.

---

## Estrategia de Branches

O projeto utiliza tres branches permanentes que representam ambientes:

```text
feature/fix branch --> develop --> staging --> main
                       (QA)       (homolog)   (producao)
```

| Branch | Ambiente | Proposito | Quem faz merge |
|--------|----------|-----------|----------------|
| `main` | Producao | Codigo estavel e validado | Admin |
| `staging` | Homologacao | Validacao pre-producao | Admin |
| `develop` | Desenvolvimento | Integracao de features | Admin |

### Regras fundamentais

- **NUNCA** commitar diretamente em `main`, `staging` ou `develop`
- **NUNCA** fazer force push em branches protegidas
- **NUNCA** deletar branches protegidas
- Feature branches **sempre** saem de `main`
- Todo codigo chega a `main` via PR aprovado

### Nomenclatura de branches

| Prefixo | Uso | Exemplo |
|---------|-----|---------|
| `feat/` | Nova funcionalidade | `feat/appointment-filtering` |
| `fix/` | Correcao de bug | `fix/session-timeout` |
| `chore/` | Manutencao, tooling, config | `chore/update-dependencies` |
| `refactor/` | Reestruturacao sem mudar comportamento | `refactor/extract-parser` |
| `docs/` | Documentacao | `docs/api-reference` |
| `test/` | Adicao/atualizacao de testes | `test/enrichment-coverage` |

---

## Protecao de Branches

As seguintes regras de protecao sao aplicadas via **GitHub Rulesets**:

### `main` (producao)

| Regra | Valor |
|-------|-------|
| Require PR before merge | Sim |
| Required approvals | 1 (Admin) |
| Require code owner review | Sim |
| Require status checks | `backend`, `frontend` |
| Require branches up to date | Sim |
| Block force push | Sim |
| Block deletion | Sim |
| Require linear history | Nao (merge commits permitidos para promocao) |
| Bypass actors | Nenhum |

### `staging` (homologacao)

| Regra | Valor |
|-------|-------|
| Require PR before merge | Sim |
| Required approvals | 1 (Admin) |
| Require status checks | `backend`, `frontend` |
| Block force push | Sim |
| Block deletion | Sim |

### `develop` (desenvolvimento)

| Regra | Valor |
|-------|-------|
| Require PR before merge | Sim |
| Required approvals | 1 (Admin) |
| Require status checks | `backend`, `frontend` |
| Block force push | Sim |
| Block deletion | Sim |

---

## Fluxo de Trabalho

### 1. Criar feature branch

```bash
# Sempre a partir de main
git checkout main
git pull origin main
git checkout -b feat/my-feature
```

### 2. Desenvolver

```bash
# Ler a spec relevante antes de codar
# Se nao existe spec, criar em docs/specs/features/ primeiro

# Implementar e testar
poetry run pytest tests/ -v
pnpm --prefix admin test

# Lint e formatacao
poetry run ruff check src/ tests/ --fix
poetry run ruff format src/ tests/
pnpm --prefix admin lint
```

### 3. Commitar

```bash
git add <arquivos-especificos>
git commit -m "feat: add appointment filtering by procedure code"
```

### 4. Abrir PR para `develop`

```bash
git push origin feat/my-feature
gh pr create --base develop --title "feat: add appointment filtering" --label enhancement
```

### 5. Promocao entre ambientes

Apos merge em `develop`, o codigo e promovido via PRs de promocao:

```text
develop --> staging (PR de promocao, merge commit)
staging --> main (PR de promocao, merge commit, requer code owner review)
```

Detalhes completos em [`PROMOTION_FLOW.md`](docs/workflows/PROMOTION_FLOW.md).

---

## Convencoes de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```text
<tipo>: <descricao curta em ingles>

[corpo opcional]
```

### Tipos permitidos

| Tipo | Quando usar |
|------|-------------|
| `feat` | Nova funcionalidade |
| `fix` | Correcao de bug |
| `chore` | Manutencao, tooling, config |
| `refactor` | Reestruturacao sem mudar comportamento |
| `docs` | Documentacao |
| `test` | Testes |

### Regras

- Mensagem em **ingles**
- Primeira linha com no maximo **72 caracteres**
- Verbo no imperativo: "add", "fix", "update" (nao "added", "fixes")
- **NUNCA** incluir `Co-Authored-By` ou atribuicao a agentes de IA
- **NUNCA** incluir informacoes de PII na mensagem

---

## Pull Requests

### Abrindo um PR

1. Use o [template de PR](.github/PULL_REQUEST_TEMPLATE.md)
2. Preencha **todas** as secoes
3. Adicione labels apropriadas (veja [Labels](#labels))
4. O destino de PRs de feature e sempre `develop`

### Requisitos para merge

- [ ] CI passa (backend + frontend)
- [ ] Aprovacao do code owner (@Garbiati)
- [ ] Nenhum PII exposto em logs
- [ ] Nenhum secret commitado
- [ ] Spec vinculada (se aplicavel)
- [ ] Testes novos para funcionalidade nova

### Estrategia de merge

| Tipo de PR | Estrategia |
|------------|------------|
| Feature/fix → `develop` | Squash merge ou merge commit |
| Promocao (`develop` → `staging` → `main`) | **Merge commit** (preserva historico) |

---

## Code Review

### O que o reviewer verifica

1. **Conformidade com a spec** — implementacao segue a spec definida
2. **Seguranca** — sem PII em logs, sem secrets, sem SQL injection, sem XSS
3. **Testes** — cobertura adequada, cenarios de erro testados
4. **Qualidade** — codigo legivel, sem over-engineering, sem duplicacao
5. **Performance** — sem N+1 queries, sem loops desnecessarios
6. **Convencoes** — codigo em ingles, docs em portugues, conventional commits

### Tempo de resposta esperado

- PRs abertas durante a semana: review em ate **48 horas**
- PRs criticas (fix de seguranca): review **prioritario**

---

## Labels

### Tipo de mudanca (obrigatorio)

| Label | Commit prefix | Cor |
|-------|---------------|-----|
| `enhancement` | `feat:` | `#a2eeef` |
| `bug` | `fix:` | `#d73a4a` |
| `chore` | `chore:` | `#e4e669` |
| `refactor` | `refactor:` | `#c5def5` |
| `documentation` | `docs:` | `#0075ca` |
| `test` | `test:` | `#bfdadc` |

### Escopo (quando aplicavel)

| Label | Quando usar |
|-------|-------------|
| `security` | Toca em auth, validacao, headers, PII |
| `promotion` | PR de promocao entre ambientes |
| `breaking-change` | Mudanca incompativel com versao anterior |

---

## Ambiente de Desenvolvimento

### Pre-requisitos

| Ferramenta | Versao |
|------------|--------|
| Docker + Docker Compose | latest |
| Python | 3.12+ |
| Poetry | 1.8+ |
| Node.js | 22+ |
| pnpm | 9+ |

### Setup rapido

```bash
# Clonar
git clone git@github.com:Garbiati/regula-hub.git
cd regula-hub

# Backend
poetry install
poetry run pre-commit install

# Frontend
pnpm --prefix admin install

# Docker (recomendado para dev completo)
cp .env.example .env
# Editar .env com suas configuracoes
docker compose up -d
```

### Comandos essenciais

```bash
# Backend
poetry run pytest tests/ -v              # testes
poetry run ruff check src/ tests/ --fix  # lint + fix
poetry run ruff format src/ tests/       # format
poetry run bandit -c pyproject.toml -r src/  # SAST

# Frontend
pnpm --prefix admin test        # testes
pnpm --prefix admin lint        # lint
pnpm --prefix admin build       # build

# Pre-commit (roda tudo)
poetry run pre-commit run --all-files
```

---

## Politica de Idioma

| Artefato | Idioma |
|----------|--------|
| Codigo-fonte | **Ingles** |
| Comentarios no codigo | **Ingles** |
| Commits e PRs | **Ingles** |
| Branch names | **Ingles** |
| Logs | **Ingles** |
| Documentacao (docs/, specs/) | **Portugues (pt-BR)** |
| README, CONTRIBUTING | **Portugues (pt-BR)** |
| Issues | **Portugues (pt-BR)** |

**Excecao:** Termos de dominio do SisReg permanecem em portugues no codigo (ex: `Videofonista`, `fichaAmbulatorial`).

---

## Seguranca e LGPD

### Regras inviolaveis

- **NUNCA** logar dados de pacientes (CPF, CNS, telefone, nome) em texto plano
- **NUNCA** commitar secrets (`.env`, credenciais, chaves privadas)
- **NUNCA** expor PII em respostas de API alem do necessario
- **NUNCA** fazer operacoes de escrita nos sistemas de regulacao
- Dados sensíveis em logs **devem ser mascarados** (`mask_username()`)
- Credenciais armazenadas com **Fernet (AES-128-CBC + HMAC)**

### Reportando vulnerabilidades

Para reportar uma vulnerabilidade de seguranca, **NAO** abra uma issue publica. Envie um email para: `a.garbiati@gmail.com` com:

1. Descricao da vulnerabilidade
2. Passos para reproduzir
3. Impacto potencial
4. Sugestao de correcao (se tiver)

---

## Niveis de Permissao

### Atual

| Nivel | Permissoes | Quem |
|-------|-----------|------|
| **Admin** | Tudo (merge, rulesets, settings, deploy) | @Garbiati |

### Futuro (plano de delegacao)

Quando o projeto tiver colaboradores regulares, sera implementado um sistema gradual de permissoes:

| Nivel | Permissoes | Como obter |
|-------|-----------|------------|
| **Contributor** | Abrir issues e PRs via fork | Qualquer pessoa |
| **Triage** | Gerenciar issues e labels | Convite do Admin apos contribuicao consistente |
| **Collaborator** | Push em feature branches, fazer code review | Convite do Admin apos 3+ PRs aprovados |
| **Maintainer** | Aprovar PRs, merge em `develop` | Convite do Admin apos 6 meses de contribuicao ativa |
| **Admin** | Tudo | Apenas o owner do repositorio |

### Criterios para elevacao

1. **Contributor → Triage:** 2+ issues ou PRs aceitos
2. **Triage → Collaborator:** 3+ PRs aprovados e merged
3. **Collaborator → Maintainer:** 6 meses de contribuicao ativa + conhecimento demonstrado das specs

A elevacao de permissoes e revisada trimestralmente pelo Admin.

---

## Leitura Obrigatoria

Antes de contribuir, leia estes documentos na ordem:

1. [`CONSTITUTION.md`](docs/specs/CONSTITUTION.md) — Principios inviolaveis
2. [`BUSINESS_RULES.md`](docs/specs/BUSINESS_RULES.md) — Regras de dominio
3. [`TECH_SPEC.md`](docs/specs/TECH_SPEC.md) — Arquitetura tecnica
4. [`BACKEND_GUARDRAILS.md`](docs/specs/BACKEND_GUARDRAILS.md) — Normas backend
5. [`ADMIN_FRONTEND_ARCHITECTURE.md`](docs/specs/features/ADMIN_FRONTEND_ARCHITECTURE.md) — Normas frontend

---

## Duvidas?

Abra uma [issue](https://github.com/Garbiati/regula-hub/issues) com a label `question`.
