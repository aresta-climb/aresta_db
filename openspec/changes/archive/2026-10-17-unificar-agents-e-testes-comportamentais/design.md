# Design

## Context

Conforme detalhado em `proposal.md`, os 6 repositórios do ecossistema (`aresta_db`, `aresta_api`, `aresta_app`, `aresta_backend`, `arestaclimb.com` e `fixalog`) evoluíram em momentos distintos, gerando divergências de nomenclatura (`AGENTS.md`, `AGENT.md`, `PRINCIPIOS.md`), referências cruzadas quebradas e ausência de diretrizes claras sobre a natureza dos testes unitários. A Fase 1 estabelece a governança unificada em todos os 6 repositórios, preparando o terreno para a Fase 2 (migração dedicada dos testes com mocks no `aresta_db`) e habilitando a evolução orgânica imediata nos demais repositórios.

## Goals / Non-Goals

**Goals:**
- Estabelecer uma arquitetura canônica de 8 princípios (`AGENTS.md`) compartilhada entre os 6 repositórios, onde os princípios I a VII são universais e o princípio VIII (sempre o último) concentra as regras específicas de cada repositório.
- Resolver formalmente a tensão entre **100% de cobertura** e **Behavior-Driven Testing (sem mocks)** através do design do código de produção e do uso de bibliotecas `test-only` de Fakes determinísticos testados (`*_fake_test`).
- Eliminar fontes duplicadas ou obsoletas de regras (`.agents/skills/principios_desenvolvimento/` no `aresta_db` e `.agents/agents.md` no `fixalog`) e sincronizar todos os arquivos `openspec/config.yaml` e documentações.

**Non-Goals:**
- Refatorar nesta Fase 1 os 101 arquivos de teste existentes no `aresta_db` que utilizam `unittest.mock` / `MagicMock` (isso será escopo de uma mudança dedicada na Fase 2).
- Reescrever em lote os testes legados nos demais repositórios fora do fluxo orgânico da Regra do Escoteiro (Princípio VII), exceto os ajustes pontuais de referência textual a `AGENTS.md` em `beta_proto_test.py` e `test_structure_mirror_test.dart`.

## Decisions

### 1. Estrutura Canônica de 8 Princípios (I–VII Universais + VIII Específico no Final)
- **Escolha**: Padronizar todos os 6 arquivos `AGENTS.md` com exatamente a mesma sequência nos itens I a VII, posicionando as diretrizes exclusivas do repositório sempre no item **VIII**:
  ```text
  +-------------------------------------------------------------------+
  | I.   Tudo em Portugues                                            |
  | II.  Modularidade e Desacoplamento (Library-First)                |
  | III. Testes Orientados a Comportamento e Espelhamento 1:1         |
  | IV.  100% de Cobertura Comportamental e TDD (Red-Green-Refactor)  |
  | V.   Fidelidade de Producao, Anti-Mocking e Fakes Test-Only       |
  | VI.  Simplicidade, Anti-Abstracao e Documentacao Continua         |
  | VII. Inegociabilidade Perante Codigo Legado (Regra do Escoteiro)  |
  +-------------------------------------------------------------------+
  | VIII. Diretrizes Especificas do Repositorio (Sempre por ultimo)   |
  +-------------------------------------------------------------------+
  ```
- **Racional**: Ter números fixos (I a VII) para os princípios universais permite que humanos, agentes e revisões de código referenciem "Princípio III" ou "Princípio V" com o mesmo significado em qualquer repositório da organização, mantendo as particularidades tecnológicas isoladas no Princípio VIII.
- **Alternativas consideradas**: Manter numerações independentes por repositório (descartado, pois gera confusão e erros de cópia/cola como os encontrados no `fixalog` e `aresta_db`).

### 2. Resolução do Conflito entre 100% de Cobertura e Behavior-Driven Testing pelo Design
- **Escolha**: Manter tanto o **espelhamento 1:1 por arquivo** quanto os **100% de cobertura**, proibindo simultaneamente *change-detector tests* e *mocks internos*. A conciliação ocorre por três regras de design:
  1. Se um código foi separado em um arquivo próprio, ele possui por definição uma interface pública e comportamentos próprios que justificam seu arquivo `_test`.
  2. Se uma linha ou branch não pode ser exercitada através de um comportamento observável na interface pública, trata-se de código morto, programação defensiva redundante ou acoplamento indevido de I/O no código de produção — devendo ser resolvido refatorando/simplificando o código de produção, e nunca usando `mock.patch` ou acessando membros privados.
  3. Caminhos de erro de I/O são testados como comportamentos reais injetando Fakes determinísticos configuráveis em modo de falha.
- **Racional**: Transforma a métrica de 100% de cobertura de um incentivo para mocks artificiais em um detector de código morto e acoplamento.

### 3. Bibliotecas `test-only` de Fakes Determinísticos com Testes Próprios (`*_fake_test`)
- **Escolha**: Determinar no Princípio V que dependências de fronteira externa devem possuir implementações Fake determinísticas em memória organizadas como bibliotecas `test-only` compartilhadas (evitando reimplementação por arquivo de teste). Como qualquer biblioteca sob o Princípio II e III, cada arquivo `*_fake` deve obrigatoriamente ter seu par `*_fake_test` garantindo que o Fake honra o contrato de produção.
- **Racional**: Um Fake sem testes próprios pode divergir silenciosamente do contrato real ou conter bugs na simulação de estados e falhas, comprometendo a confiabilidade de todos os testes que dependem dele.

### 4. Mapeamento do Princípio VIII por Repositório
- **`aresta_db`**: *VIII. Edições de Estado via Comandos do Histórico (Undo/Redo)* (`QUndoCommand` na pilha global `historico`).
- **`aresta_api`**: *VIII. Design e Evolução de Schemas Protobuf* (encapsulamento de `Enum` em mensagem dedicada com `INDEFINIDO = 0`, encapsulamento de `oneof` com `(aresta.mensagem_formato_na_ui) = ONEOF_CONTEUDO;`, limite de no máximo um campo `conteudo_markdown` por mensagem e geração via `build.py`).
- **`aresta_app`**: *VIII. Testes de Widget, Isolates Reais e Arquitetura Reativa* (priorização de Widget Tests para fluxos de UI e uso de micro-servidor HTTP local em loopback para testes de sincronização em background via `Isolate`).
- **`aresta_backend`**: *VIII. Eficiência de Borda (Edge-First) e Isolamento Compartilhado* (Edge Functions e Cloudflare Workers mantidos como camadas finas de roteamento/segurança/validação, delegando regras de negócio e parsers para bibliotecas autocontidas em `compartilhado/`).
- **`arestaclimb.com`**: *VIII. Eficiência Client-Side First e Arquitetura Web Leve* (delegação de processamento para o navegador, arquitetura MPA em Vanilla JS/CSS + Vite sem frameworks pesados).
- **`fixalog`**: *VIII. Operação Offline-First e Integridade Pericial Criptográfica* (funcionamento 100% offline-first com persistência local e garantia de verificabilidade criptográfica X.509/XML-DSig e cadeia de custódia nos laudos EPUB 3 e PDF).

### 5. Consolidação em `AGENTS.md` como Fonte Única (Remoção de Skills Redundantes)
- **Escolha**: Remover `.agents/skills/principios_desenvolvimento/` do `aresta_db` e `.agents/agents.md` do `fixalog`, além de configurar `openspec/config.yaml` nos repositórios que utilizam OpenSpec para referenciar diretamente o `AGENTS.md` da raiz.
- **Racional**: O Antigravity já carrega nativamente o `AGENTS.md` da raiz como regra prioritária de workspace; manter skills separadas com cópias parciais dos princípios causava deriva documental.

## Risks / Trade-offs

- **[Risco] Submódulos Git (`aresta_api` e `arestaclimb.com` dentro de `aresta_app` e `fixalog`) ficarem com ponteiros desatualizados após edição** → **Mitigação**: Atualizar diretamente a raiz de cada repositório (`aresta_db/aresta_api` e `arestaclimb.com`) e verificar a consistência dos arquivos em todos os 6 diretórios.
- **[Risco] Agentes futuros imitarem os 101 arquivos de teste com mocks ainda presentes no `aresta_db` antes da conclusão da Fase 2** → **Mitigação**: O novo **Princípio VII (Inegociabilidade Perante Código Legado)** alerta explicitamente contra o viés de imitação de código vizinho e proíbe replicar mocks existentes, exigindo refatoração do trecho tocado.
