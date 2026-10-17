# Proposal

## Why

Atualmente, os princípios de engenharia do ecossistema Aresta estão fragmentados e inconsistentes entre os 6 repositórios (`aresta_db`, `aresta_api`, `aresta_app`, `aresta_backend`, `arestaclimb.com` e `fixalog`): alguns usam `AGENTS.md`, outros `PRINCIPIOS.md` ou `AGENT.md`, o `aresta_api` não possui arquivo próprio, existem erros de cópia/cola entre projetos e referências quebradas na documentação e em skills duplicadas. Além disso, a ausência de diretrizes explícitas sobre **como** escrever bons testes unitários (orientados a comportamento, um teste por *behavior*, sem *change-detector tests* e sem *mocks*, apoiados em bibliotecas `test-only` de Fakes determinísticos) tem levado agentes e desenvolvedores a acoplarem testes na implementação interna e abusarem de mocks para atingir 100% de cobertura.

## What Changes

- **Padronização Canônica de `AGENTS.md` nos 6 Repositórios (Fase 1)**:
  - Unificação dos princípios I a VII em todos os 6 repositórios (`aresta_db`, `aresta_api`, `aresta_app`, `aresta_backend`, `arestaclimb.com` e `fixalog`), deixando a seção **VIII** (sempre a última) dedicada às diretrizes arquiteturais específicas de cada repositório.
  - Renomeação de `fixalog/PRINCIPIOS.md` e `aresta_backend/AGENT.md` para `AGENTS.md`, e criação do `AGENTS.md` na raiz do submódulo `aresta_api`.
- **Evolução da Filosofia de Testes (Behavior-Driven, Anti-Change-Detector e Anti-Mocking)**:
  - Estabelecimento de **Testes Orientados a Comportamento (1 teste por *behavior*)** exercitando exclusivamente a API pública de cada módulo, mantendo o espelhamento 1:1 (`arquivo` -> `arquivo_test`) sob a premissa de que todo arquivo separado possui uma interface pública própria a ser validada.
  - Resolução explícita entre **100% de Cobertura** e **Testes de Comportamento**: toda linha de produção deve justificar sua existência por um comportamento observável; linhas inalcançáveis pela API pública indicam código morto ou acoplamento no código de produção que deve ser removido ou refatorado, nunca contornado com mocks ou chamadas a métodos privados.
  - Proibição de mocks para código interno e obrigatoriedade de **bibliotecas `test-only` de Fakes determinísticos** para fronteiras externas — sendo que cada biblioteca Fake (`*_fake`) é uma biblioteca de primeira classe e deve possuir seu próprio arquivo de teste espelhado (`*_fake_test`).
- **Cláusula de Inegociabilidade Perante Código Legado (Princípio VII)**:
  - Formalização de que código ou testes existentes fora do padrão não servem de desculpa ou precedente; qualquer trecho tocado deve ser refatorado para cumprir o `AGENTS.md`.
- **Consolidação de Fonte Única da Verdade e Limpeza de Referências**:
  - Remoção da skill redundante `.agents/skills/principios_desenvolvimento/` no `aresta_db` e do arquivo experimental `.agents/agents.md` no `fixalog`.
  - Atualização de todas as referências de `PRINCIPIOS.md` e `AGENT.md` para `AGENTS.md` em `openspec/config.yaml`, `README.md`, `CONTRIBUTING.md`, `GUIA_DO_DESENVOLVEDOR.md` e testes de governança (`beta_proto_test.py` e `test_structure_mirror_test.dart`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `principios-implementacao`: Atualiza e expande os requisitos de engenharia para contemplar a estrutura unificada de 8 princípios (`AGENTS.md`), testes orientados a comportamento (1 teste por behavior, proibição de change-detectors), cobertura comportamental de 100%, proibição de mocks internos em favor de bibliotecas `test-only` de Fakes determinísticos testados (`*_fake_test`), e inegociabilidade perante código legado.

## Impact

- **`aresta_db`**: `AGENTS.md`, `GUIA_DO_DESENVOLVEDOR.md`, `openspec/config.yaml`, `openspec/specs/principios-implementacao/spec.md` e remoção de `.agents/skills/principios_desenvolvimento/SKILL.md`.
- **`aresta_api`**: Criação de `AGENTS.md` e atualização de `README.md` e `beta_proto_test.py`.
- **`aresta_app`**: `AGENTS.md`, `openspec/config.yaml`, `CONTRIBUTING.md`, `frontend/README.md` e `frontend/lib/utils/README.md`.
- **`aresta_backend`**: Renomeação de `AGENT.md` para `AGENTS.md` e adequação ao contexto de Supabase Edge Functions e Cloudflare Workers.
- **`arestaclimb.com`**: `AGENTS.md` e `openspec/config.yaml`.
- **`fixalog`**: Renomeação de `PRINCIPIOS.md` para `AGENTS.md`, remoção de `.agents/agents.md` e atualização de `README.md`, `openspec/config.yaml`, `openspec/README.md`, `docs/ROTEIRO_INTEGRACAO_ARESTA.md` e `app/test/architecture/test_structure_mirror_test.dart`.
