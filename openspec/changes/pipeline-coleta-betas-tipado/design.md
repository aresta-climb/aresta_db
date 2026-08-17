## Context

O sistema de coleta de betas anterior disponibilizou extratores para YouTube, Vertex AI Search e DuckDuckGo, além da interface de curadoria em PyQt. Para viabilizar a orquestração autônoma e em lote via workflows do Antigravity, precisamos de uma ponte declarativa entre o banco de dados do croqui e o pipeline de extração e moderação, mantendo toda a validação de tipos estrita por Protobuf.

## Goals / Non-Goals

**Goals:**
- Definir mensagens Protobuf para tipagem estática de `vias_extraidas.yaml` e `candidatos_brutos.yaml`.
- Criar comandos CLI desacoplados (`coleta_de_betas.extrair_vias`, `coleta_de_betas.buscar`, `coleta_de_betas.salvar_staging`).
- Migrar o papel de avaliação de IA de um SDK externo para **sub-agentes nativos do Antigravity** (`AvaliadorBetas`).
- Fornecer um workflow interativo `.agents/workflows/coletar_betas.md` para orquestração ponta a ponta.
- Manter conformidade estrita com `PRINCIPIOS.md` (TDD, 100% de testes passando, código e comentários em português).

**Non-Goals:**
- Não alterar a interface gráfica de curadoria existente no PyQt (a mesma continuará consumindo `betas_pendentes.binarypb`).
- Não substituir os extratores existentes de YouTube, Vertex e DuckDuckGo, apenas integrá-los aos comandos CLI.

## Decisions

### 1. Serialização Protobuf/YAML Bidirecional
- **Decisão**: Utilizar `google.protobuf.json_format` (`MessageToDict` e `ParseDict`) acoplado ao `yaml.safe_load`/`yaml.dump` para gerar arquivos `.yaml` com tipagem garantida.
- **Alternativas consideradas**:
  - Dicionários Python puros / Pydantic: Rejeitado para manter o Protobuf como a única fonte da verdade de dados em todo o repositório (`aresta_api`).

### 2. Formato de Arquivos Intermediários
- **Decisão**:
  - `vias_extraidas.yaml`: Mensagem `ViasExtraidasCroqui`.
  - `candidatos_brutos.yaml`: Mensagem `BetasPendentes` com campos geográficos e candidatos desprovidos de score de IA.
  - `betas_pendentes.binarypb`: Mensagem `BetasPendentes` após avaliação pelos sub-agentes.
- **Alternativas consideradas**:
  - Arquivos JSON ou CSV: Rejeitado a pedido do usuário em favor de manter a consistência com os arquivos YAML do ecossistema.

### 3. Avaliação semântica via Sub-agentes Antigravity
- **Decisão**: O workflow orquestrador registrará a classe de sub-agente `AvaliadorBetas` via `define_subagent` e disparará chamadas paralelas via `invoke_subagent` para lotes de escaladas.
- **Rationale**: Elimina a necessidade de tokens de API de LLMs externas e aproveita a inteligência multimodal integrada do Antigravity.

## Risks / Trade-offs

- **[Risco] Vias sem metadados de setor ou grau**: Podem gerar buscas excessivamente genéricas.
  - *Mitigação*: O script `extrair_vias` normaliza valores vazios e usa o nome do croqui, cidade e estado como fallback para refinar a busca.
- **[Risco] Limite de contexto em lotes grandes**: Sub-agentes podem ser sobrecarregados se receberem muitas vias de uma vez.
  - *Mitigação*: O workflow orquestrador particiona os candidatos em lotes de 5 a 10 escaladas por sub-agente.
