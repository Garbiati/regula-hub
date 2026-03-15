# Integração CadWeb (Consulta CNS) para Enriquecimento de Dados

## Contexto

O `ptm-regulation-service` (.NET 9) precisa de `patientCPF`, `patientMotherName` e um `bestPhone` confiável. Esses dados **não existem** na `fichaAmbulatorial` do SisReg, mas **existem** na **Consulta CNS / CadWeb** (`/cgi-bin/cadweb50`), acessível pelo Videofonista dentro da mesma sessão SisReg.

## O que é o CadWeb

O CadWeb (Cadastro Web do SUS) é o sistema de cadastro nacional de usuários do SUS, acessível via SisReg pela funcionalidade "Consulta CNS". Permite consultar dados demográficos completos de um paciente a partir do CNS.

### Fluxo de Acesso

1. Videofonista acessa "CONSULTA CNS" no menu do SisReg
2. O sistema abre `/cgi-bin/cadweb50?standalone=1`
3. Insere o CNS do paciente e clica "Pesquisar"
4. Resultado retorna página com dados completos do paciente

### Endpoint

```
GET /cgi-bin/cadweb50?metodo=pesquisar&cpf_cns={CNS}&standalone=1
```

### Estrutura da Resposta HTML

A página de resultado contém seções em tabelas HTML:

- **DADOS PESSOAIS**: CNS, Nome, Nome da Mãe, Nome do Pai, Sexo, Data de Nascimento
- **ENDEREÇO**: Logradouro, Bairro, CEP, Município
- **CONTATOS**: Tabela com Tipo Telefone, DDD, Número (ex: CELULAR, RESIDENCIAL)
- **DOCUMENTOS**: CPF

Layout usa `<td><b>Label:</b></td><td>Valor</td>` (key-value em tabela).

## Campos Extraídos

| Campo | Tipo | Seção CadWeb | Uso |
|-------|------|-------------|-----|
| `cpf` | string | DOCUMENTOS | `patientCPF` no detail |
| `mother_name` | string | DADOS PESSOAIS | `patientMotherName` no listing |
| `father_name` | string | DADOS PESSOAIS | Disponível para uso futuro |
| `sex` | string | DADOS PESSOAIS | Disponível para uso futuro |
| `phone_type` | string | CONTATOS | Tipo do telefone (CELULAR preferido) |
| `phone_ddd` | string | CONTATOS | DDD do telefone |
| `phone_number` | string | CONTATOS | Número do telefone |

## Tratamento de Erros

- **CNS não encontrado**: CadWeb retorna página sem "DADOS PESSOAIS" → `None` (graceful)
- **CadWeb indisponível**: Exceção capturada → enrichment continua sem CadWeb
- **CNS PROVISÓRIO**: Pode não retornar resultado → fallback para dados da fichaAmbulatorial

## Cache por CNS

Dentro de uma sessão de enrichment, o mesmo paciente pode aparecer em múltiplos agendamentos. O resultado do CadWeb é cacheado por CNS para evitar queries duplicadas.

## Impacto nos Endpoints Absens

### Listing (`patientMotherName`)

| Antes | Depois |
|-------|--------|
| `""` (indisponível) | Nome da mãe do CadWeb |

### Detail (`patientCPF`, `bestPhone`)

| Campo | Antes | Depois |
|-------|-------|--------|
| `patientCPF` | `null` | CPF do CadWeb |
| `bestPhone` | fichaAmbulatorial (inconsistente) | CELULAR do CadWeb (preferido) ou fichaAmbulatorial |

## Performance

| Métrica | Antes | Depois |
|---------|-------|--------|
| Requests por code | 1 (detail) | 2 (detail + cadweb) |
| Tempo por code | ~2s | ~4s |
| Com cache (mesmo paciente) | N/A | CadWeb cached → ~2s |
| 30 codes, 3 credentials, sem(5) | ~20s | ~40s |
