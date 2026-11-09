# avaliador-betas-subagente Specification

## Purpose
Define a avaliação semântica e pontuação de candidatos a betas (`betas_nao_scorados`) por sub-agentes `AvaliadorBetas` orquestrados via skill e servidor MCP do Editor Aresta.

## Requirements

### Requirement: Avaliação de Betas por Sub-agentes Antigravity
O sistema SHALL delegar a avaliação semântica dos itens presentes em `betas_nao_scorados` a sub-agentes nativos do Antigravity (`AvaliadorBetas`), lendo e gravando diretamente no `Croqui` aberto no Editor via servidor MCP (ou no arquivo `curadoria_betas.md`), sem depender de SDKs externos de IA ou arquivos YAML intermediários avulsos.

#### Scenario: Avaliação de lote de candidatos por sub-agente
- **WHEN** um sub-agente `AvaliadorBetas` é invocado com um lote de escaladas contendo itens em `betas_nao_scorados`
- **THEN** ele MUST analisar os metadados geográficos (nome da via, grau, setor, grupo, pico, cidade e estado), o título e os `snippets` coletados de cada candidato.
- **THEN** ele MUST atribuir um score de confiança (0-100) e uma justificativa textual (`llm_reasoning`).
- **THEN** os candidatos avaliados MUST ser movidos de `betas_nao_scorados` para `betas_nao_revisados` no modelo do croqui via MCP (`aresta_alterar_campo`), atualizando a interface do Editor em tempo real.

### Requirement: Orquestração no Workflow Antigravity
O sistema SHALL disponibilizar uma skill dedicada (`.agents/skills/avaliar_betas_croqui/SKILL.md`) e atualizar o workflow `.agents/workflows/coletar_betas.md` para operar de forma integrada com o servidor MCP do Editor Aresta e com o campo `curadoria_betas` do `Croqui`.

#### Scenario: Execução orquestrada do workflow
- **WHEN** o usuário solicita ao agente conectado via MCP a avaliação dos betas não scorados (seguindo as instruções da aba **Betas** ou invocando `/coletar_betas`)
- **THEN** o agente MUST carregar a skill `avaliar_betas_croqui`, ler os `betas_nao_scorados` do croqui via MCP, particionar em lotes para sub-agentes `AvaliadorBetas` em paralelo e persistir os itens pontuados em `betas_nao_revisados`.
