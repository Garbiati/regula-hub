# Fluxo de Promocao entre Ambientes

## Visao Geral

O codigo segue um fluxo de promocao linear entre ambientes:

```text
feature/fix branch --> dev --> staging --> master
                       (QA)   (homolog)   (producao)
```

Cada transicao entre ambientes e feita via **PR de promocao** — um tipo especifico de pull request que promove codigo ja testado e aprovado, sem introduzir alteracoes novas.

## PR de Feature vs PR de Promocao

| Aspecto | PR de Feature | PR de Promocao |
|---------|---------------|----------------|
| Origem | Branch de feature (`feat/`, `fix/`, `chore/`) | Branch de ambiente (`dev`, `staging`) |
| Destino | `dev` | Proximo ambiente (`staging`, `master`) |
| Template | `.github/PULL_REQUEST_TEMPLATE.md` | Template proprio (ver abaixo) |
| Revisao de codigo | Obrigatoria (analise tecnica) | Verificacao de integridade (ja foi revisado) |
| Estrategia de merge | Squash ou merge commit | **Merge commit** (obrigatorio) |
| Labels | Tipo do commit (`enhancement`, `bug`, etc.) | Labels originais + `promotion` |

## Regras por Ambiente

### dev -> staging

- **Aprovacoes necessarias:** 1
- **Code owner review:** Nao obrigatorio
- **Bypass actors:** Org Admin, Repo Admin, code-owners-tc-backend, devops
- **No comando `promotion-dev-to-master`:** auto-merge via `--admin`

### staging -> master

- **Aprovacoes necessarias:** 1
- **Code owner review:** Obrigatorio
- **Bypass actors:** Org Admin, Repo Admin, code-owners-tc-backend, devops
- **No comando `promotion-dev-to-master`:** aprovacao e merge manuais pelo desenvolvedor
- **No comando `promotion-dev-to-master-y`:** auto-merge via `--admin` (pipeline completo)

## Template de PR de Promocao

```markdown
## Promotion: {source} -> {target}

### Source

- **Source branch:** `{source}` ({commit_sha})
- **Target branch:** `{target}` ({commit_sha})
- **Promotion type:** Environment promotion

### PRs Included

| PR | Title | Labels | Merged |
|----|-------|--------|--------|
| #{n} | {title} | {labels} | {date} |

### Changes Summary

{lista de mudancas dos PRs originais}

### Diff Stats

{N} files changed, {N} insertions(+), {N} deletions(-)

### Validation

- [x] All tests pass on `{source}`
- [x] Original PRs were reviewed and approved before merge
- [x] No new code — promotion only (identical to `{source}`)

### Merge Strategy

Merge commit (preserve commit history across environments)
```

### Convencoes do Template

- **Titulo:** `promote: {source} to {target} — {resumo} (PR #N, #M)`
- **Labels:** Todas as labels dos PRs originais + `promotion`
- **Corpo:** Em ingles (artefato de codigo, conforme politica de idioma)
- **Estrategia de merge:** Sempre merge commit — **nunca squash** em PRs de promocao

## PR Chain (Rastreabilidade)

Para PRs de staging -> master, inclua a tabela de rastreabilidade completa:

```markdown
### PR Chain

| Step | PR | Title | Environment |
|------|----|-------|-------------|
| 1 | #N | {titulo original} | feature -> dev |
| 2 | #M | promote: dev to staging — ... | dev -> staging |
| 3 | **This PR** | promote: staging to master — ... | staging -> master |
```

Isso garante rastreabilidade total da origem do codigo ate producao.

## Comandos de Promocao

Documentados no [CLAUDE.md](../../CLAUDE.md) do projeto. O staging e implicito — ambos os comandos promovem dev -> staging -> master em sequencia.

### `promotion-dev-to-master`

1. **dev -> staging:** Cria PR, auto-analise, auto-merge via `gh pr merge --admin --merge`
2. **staging -> master:** Cria PR, auto-analise, **aprovacao e merge manuais** pelo desenvolvedor

### `promotion-dev-to-master-y`

O sufixo `-y` significa "yes to merge" — pipeline completo sem paradas.

1. **dev -> staging:** Cria PR, auto-analise, auto-merge via `gh pr merge --admin --merge`
2. **staging -> master:** Cria PR, auto-analise, **auto-merge** via `gh pr merge --admin --merge`

## Checklist de Promocao

Antes de criar uma PR de promocao, verifique:

- [ ] Todos os testes passam no ambiente de origem
- [ ] Nao ha PRs pendentes no ambiente de origem que deveriam ser incluidos
- [ ] Os PRs originais foram revisados e aprovados
- [ ] Nao ha conflitos entre as branches
- [ ] As labels corretas estao disponiveis (incluindo `promotion`)

## Exemplos Reais

### PR #2 — dev -> staging

```text
Titulo: promote: dev to staging — security hardening (PR #1)
Labels: chore, security, promotion
Merge: gh pr merge 2 --merge --admin
```

### PR #3 — staging -> master

```text
Titulo: promote: staging to master — security hardening (PR #1, #2)
Labels: chore, security, promotion
Merge: manual (aprovacao + merge pelo desenvolvedor)
```
