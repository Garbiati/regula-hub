# RegulaHub — Sobre o Projeto

## O Problema

A regulação do SUS opera através de sistemas como **SisReg III**, **e-SUS Regulação**, **SIGA Saúde**, **CARE Paraná** e **SER (RJ)**. Cada sistema possui múltiplas contas por unidade de saúde — videofonistas, solicitantes, executantes, reguladores.

Na prática, um operador da regulação no Amazonas precisa:

1. Abrir o SisReg III manualmente
2. Fazer login em **11 contas diferentes** de solicitante
3. Navegar por menus complexos para cada conta
4. Copiar dados para planilhas Excel
5. Repetir para cada data de referência

Esse processo manual consome horas por dia, é propenso a erros e não escala.

## A Solução: Sistema Virtual

O **RegulaHub** funciona como uma camada de integração que:

- **Agrega múltiplas contas** em uma visão unificada
- **Automatiza a coleta** de dados via HTTP direto (sem browser automation)
- **Persiste seleções** de operadores no banco de dados
- **Suporta múltiplos sistemas** de regulação (SISREG, e-SUS, SIGA, CARE, SER)

### Arquitetura

```
Operador → Admin UI (Next.js) → API (FastAPI) → Sistema de Regulação (HTTP)
                                      ↕
                                  PostgreSQL
```

O operador seleciona quais contas usar, e o sistema consulta todas simultaneamente.

## Usuários

### Personas

| Persona | Descrição | Sistemas |
|---------|-----------|----------|
| **Videofonista** | Visão estadual, lista todos os agendamentos | SISREG |
| **Solicitante** | Visão por unidade, cria solicitações | SISREG, e-SUS, SIGA, CARE, SER |
| **Executante** | Visão da unidade executante | SISREG, e-SUS, SER |
| **Regulador** | Revisão e aprovação de solicitações | e-SUS, SIGA, CARE, SER |
| **Gestor** | Supervisão administrativa | SIGA |
| **Auditor** | Acesso somente leitura para auditoria | CARE |

### Modelo de Usuários

O RegulaHub possui seus próprios **usuários de plataforma** (operadores e administradores), separados das credenciais dos sistemas externos. As seleções de operadores são salvas por usuário no banco de dados.

## Sistemas Suportados

| Sistema | Abrangência | Status |
|---------|-------------|--------|
| **SISREG III** | Nacional (foco: AM) | Operacional |
| **e-SUS Regulação** | Nacional | Planejado |
| **SIGA Saúde** | São Paulo (SP) | Planejado |
| **CARE Paraná** | Paraná (PR) | Planejado |
| **SER (RJ)** | Rio de Janeiro (RJ) | Planejado |

## Segurança e LGPD

- **Criptografia**: Senhas armazenadas com Fernet (AES-128-CBC + HMAC)
- **Somente leitura**: Nenhuma operação de escrita nos sistemas de regulação
- **Sem log de PII**: CPF, CNS, telefone e nome de pacientes nunca aparecem em logs
- **Acesso controlado**: API protegida por API Key, sem exposição pública
- **Sessão efêmera**: Login/logout a cada requisição, sem sessões persistentes

## Escopo Atual

- **Estado**: Amazonas (AM)
- **Sistema**: SISREG III
- **Operadores**: 11 contas de videofonista/solicitante
- **Funcionalidade**: Consulta de agendamentos, extração de detalhes, pipeline de sincronização
