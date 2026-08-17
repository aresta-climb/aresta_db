## Context

O sistema de coleta de betas anterior disponibilizou extratores para YouTube, Vertex AI Search e DuckDuckGo, além da interface de curadoria em PyQt. Para viabilizar a orquestração autônoma e em lote via workflows do Antigravity, precisamos de uma ponte declarativa entre o banco de dados do croqui e o pipeline de extração e moderação, mantendo toda a validação de tipos estrita por Protobuf e estrita conformidade com os `PRINCIPIOS.md` do repositório.

## Goals / Non-Goals

**Goals:**
- Definir mensagens Protobuf para tipagem estática de `vias_extraidas.yaml` e `candidatos_brutos.yaml`.
- Criar bibliotecas funcionais independentes (Library-First) e pontos de entrada CLI (`coleta_de_betas.extrair_vias`, `coleta_de_betas.buscar`, `coleta_de_betas.salvar_staging`).
- Migrar o papel de avaliação de IA de um SDK externo para **sub-agentes nativos do Antigravity** (`AvaliadorBetas`).
- Fornecer um workflow interativo `.agents/workflows/coletar_betas.md` para orquestração ponta a ponta.
- Manter conformidade estrita com `PRINCIPIOS.md` (Tudo em Português, Library-First, 100% de cobertura de testes, TDD Red-Green-Refactor, Testes de Integração em Primeiro Lugar e Simplicidade/Anti-Abstração).

**Non-Goals:**
- Não alterar a interface gráfica de curadoria existente no PyQt (a mesma continuará consumindo `betas_pendentes.binarypb`).
- Não substituir os extratores existentes de YouTube, Vertex e DuckDuckGo, apenas integrá-los aos comandos e bibliotecas.

## Decisions

### 1. Aderência aos Princípios de Engenharia (`PRINCIPIOS.md`)
- **I. Tudo em Português**: Nomes de arquivos, funções, classes, variáveis, mensagens de commit e documentações 100% em português brasileiro (`extrator_vias.py`, `io_yaml.py`, `runner_busca.py`, `runner_staging.py`).
- **II. Library-First**: Cada funcionalidade é uma biblioteca independente com propósito claro; os módulos CLI são apenas camadas finas sobre as bibliotecas.
- **III & IV. 100% de Cobertura e TDD**: Todo arquivo `.py` tem seu `_test.py` co-localizado no mesmo diretório, construído no ciclo Red-Green-Refactor.
- **V. Testes de Integração em Primeiro Lugar**: Testes de ponta a ponta de I/O e persistência YAML/Protobuf estabelecidos antes dos testes unitários detalhados.
- **VI. Simplicidade e Anti-Abstração**: Uso direto dos recursos nativos do Protobuf (`google.protobuf.json_format`) sem camadas intermediárias ou frameworks desnecessários.

### 2. Serialização Protobuf/YAML Bidirecional
- **Decisão**: Utilizar `google.protobuf.json_format` (`MessageToDict` e `ParseDict`) acoplado ao `yaml.safe_load`/`yaml.dump` para gerar arquivos `.yaml` com tipagem estática garantida.
- **Alternativas consideradas**:
  - Dicionários Python puros / Pydantic: Rejeitado para manter o Protobuf como a única fonte da verdade de dados em todo o repositório (`aresta_api`).

### 3. Formato de Arquivos Intermediários
- **Decisão**:
  - `vias_extraidas.yaml`: Mensagem `ViasExtraidasCroqui`.
  - `candidatos_brutos.yaml`: Mensagem `BetasPendentes` com campos geográficos e candidatos desprovidos de score de IA.
  - `betas_pendentes.binarypb`: Mensagem `BetasPendentes` após avaliação pelos sub-agentes.
- **Alternativas consideradas**:
  - Arquivos JSON ou CSV: Rejeitado a pedido do usuário em favor de manter a consistência com os arquivos YAML do ecossistema.

### 4. Avaliação semântica via Sub-agentes Antigravity
- **Decisão**: O workflow orquestrador registrará a classe de sub-agente `AvaliadorBetas` via `define_subagent` e disparará chamadas paralelas via `invoke_subagent` para lotes de escaladas.
- **Rationale**: Elimina a necessidade de tokens de API de LLMs externas e aproveita a inteligência multimodal integrada do Antigravity.

## Risks / Trade-offs

- **[Risco] Vias sem metadados de setor ou grau**: Podem gerar buscas excessivamente genéricas.
  - *Mitigação*: O script `extrator_vias` normaliza valores vazios e usa o nome do croqui, cidade e estado como fallback para refinar a busca.
- **[Risco] Limite de contexto em lotes grandes**: Sub-agentes podem ser sobrecarregados se receberem muitas vias de uma vez.
  - *Mitigação*: O workflow orquestrador particiona os candidatos em lotes de 5 a 10 escaladas por sub-agente.
