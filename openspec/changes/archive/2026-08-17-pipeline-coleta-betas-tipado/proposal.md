## Why

O fluxo atual de coleta de betas precisa ser orquestrado de ponta a ponta de forma determinística, transparente e robusta. Para evitar chamadas opacas a SDKs ou serviços de IA externos e garantir a integridade dos dados, propomos:
1. Extração estática de vias e geração de candidatos serializados em arquivos YAML fortemente tipados por schemas Protobuf (`vias_extraidas.yaml` e `candidatos_brutos.yaml`).
2. Delegação integral da avaliação por IA para os **sub-agentes nativos do Antigravity** em paralelo, eliminando dependências de chaves e custos externos de LLM.
3. Aderência irrestrita aos `PRINCIPIOS.md` do repositório (Tudo em Português, Library-First, 100% de cobertura de testes, TDD Red-Green-Refactor e testes de integração em primeiro lugar).

## What Changes

- **Modelagem Protobuf Estática**: Criação das mensagens `EscaladaAlvoBusca` e `ViasExtraidasCroqui` em `aresta_api/proto/beta.proto`, além da inclusão de metadados geográficos (`grau`, `nome_pico`, `cidade`, `estado`) em `CandidatosBetaPorEscalada`.
- **Script CLI de Extração de Vias (`extrair_vias`)**: Biblioteca funcional e comando que lê `croqui.yaml` e os arquivos `.md` e gera `database/<croqui>/vias_extraidas.yaml` validado e tipado por `ViasExtraidasCroqui`.
- **Script CLI de Busca Concorrente (`buscar`)**: Biblioteca funcional e comando que recebe `vias_extraidas.yaml`, executa as buscas paralelas (YouTube, Vertex AI Search, DuckDuckGo) com deduplicação e gera `database/<croqui>/candidatos_brutos.yaml` tipado por `BetasPendentes`.
- **Avaliação Multimodal por Sub-agentes Antigravity**: Orquestração via `define_subagent` e `invoke_subagent` com batches paralelos que analisam contexto geográfico, títulos, snippets e thumbnails.
- **Script CLI de Staging (`salvar_staging`)**: Biblioteca funcional e comando que converte a saída avaliada dos sub-agentes no arquivo binário `database/<croqui>/betas_pendentes.binarypb`.
- **Workflow Antigravity Atualizado (`.agents/workflows/coletar_betas.md`)**: Orquestrador interativo completo integrando todas as etapas de forma determinística.

## Capabilities

### New Capabilities
- `pipeline-betas-tipado`: Comandos CLI e bibliotecas para manipulação e validação estática de `vias_extraidas.yaml` e `candidatos_brutos.yaml` com base em schemas Protobuf.
- `avaliador-betas-subagente`: Avaliação de relevância de betas distribuída e executada por sub-agentes nativos do Antigravity.

### Modified Capabilities
- `beta-model`: Adição de `EscaladaAlvoBusca`, `ViasExtraidasCroqui` e campos geográficos enriquecidos em `CandidatosBetaPorEscalada` em `beta.proto`.

## Impact

- **Protobuf**: `aresta_api/proto/beta.proto` expandido e recompilado para Python e Dart.
- **Módulo `coleta_de_betas`**: Adição de submódulos de CLI e serializadores Protobuf/YAML como bibliotecas independentes (`Library-First`).
- **Workflow**: `.agents/workflows/coletar_betas.md` atualizado para orquestrar sub-agentes `AvaliadorBetas`.
- **Testes**: 100% de cobertura unitária e testes de integração com convenção `*_test.py` co-localizada.
