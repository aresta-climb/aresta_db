# Proposal

## Why

O pipeline de coleta de betas existente opera de forma desconectada da arquitetura moderna do Editor Aresta (`CroquiModel`, histórico `QUndoCommand` e servidor MCP): ele depende de arquivos intermediários órfãos (`vias_extraidas.yaml`, `candidatos_brutos.yaml`, `betas_pendentes.binarypb`), mistura metadados transitórios de scraping/IA dentro da mensagem publicada `MidiaBeta`, casa escaladas por nome (em vez de `uid` NanoID), não suporta blogs nem evita re-scraping de links descartados, e mantém a aba **Betas** oculta e sem conexão com o modelo em memória. Precisamos unificar o ciclo de vida completo de descoberta, avaliação por IA via MCP, curadoria humana (1 a 1 com Undo/Redo) e publicação limpa em `Escalada.betas` no `compilado.binarypb`.

## What Changes

- **BREAKING** (`beta.proto` / `croqui.proto`): Simplificação de `MidiaBeta` para conter exclusivamente os dados publicados (`url`, `titulo` e `fonte`, adicionando `FonteMidia.BLOG = 3` e removendo `thumbnail_url` e campos de scraping/LLM).
- **BREAKING** (`beta.proto` / `croqui.proto`): Criação de `CandidatoMidiaBeta`, `CuradoriaBetasEscalada`, `ColecaoCuradoriaBetas` e do wrapper `ArquivoCuradoriaBetas` (`ONEOF_CONTEUDO` em `Croqui.curadoria_betas` persistido em `curadoria_betas.md`), armazenando por `escalada_uid` as listas `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados`, mantendo os arquivos `setor_*.md` exclusivos para os `betas` aprovados e removendo `curadoria_betas` na geração de `compilado.binarypb` e `compilado.yaml`.
- **Extração de Blogs e Previews Estilo WhatsApp com Cache Persistente**: Novo extrator para páginas de blog (`FonteMidia.BLOG`) com download de HTML cacheado por URL, validação de vocabulário de escalada e recorte de janelas de texto ($\pm 300$ caracteres ao redor do nome da via), filtragem automática contra URLs já presentes nas 4 listas da escalada (`betas`, `betas_nao_revisados`, `betas_nao_scorados`, `betas_rejeitados`), e resolução de miniaturas estilo WhatsApp (YouTube por ID e Blogs/Instagram via OpenGraph `og:image`) com cache offline em disco (`ProvedorImagemAresta`).
- **Aba de Revisão de Betas, Wizard de Coleta e Atalho na Aba Dados**: Habilitação da aba **Betas** no Editor integrada ao `CroquiModel` e `CroquiController` (Undo/Redo), com Wizard **"Coletar Betas..."** (seleção de escaladas e progresso), visualização em **4 seções expansíveis** (`betas_nao_revisados`, `betas_nao_scorados` com instruções para o agente MCP, `betas` aprovados e `betas_rejeitados`), ações **1 a 1** (Aprovar, Rejeitar para `betas_rejeitados` e Restaurar, sem aprovação/limpeza em lote) e componente na ficha da `Escalada` na aba **Dados** com resumo e botão **"Abrir na Revisão de Betas"**.
- **Skill MCP de Scoring e Avisos de Compilação**: Criação de skill e integração via MCP para que o agente conectado leia `betas_nao_scorados`, avalie lotes com sub-agentes `AvaliadorBetas` e promova para `betas_nao_revisados`, além de emissão de aviso (Warning) durante a compilação e no `STATUS_CROQUIS.md` quando existirem betas pendentes (`betas_nao_scorados` ou `betas_nao_revisados`).

## Capabilities

### New Capabilities
*(Nenhuma capability nova isolada; as capacidades existentes de betas serão evoluídas para refletir a arquitetura integrada).*

### Modified Capabilities
- `beta-model`: Separação entre `MidiaBeta` limpo (com adição de `FonteMidia.BLOG = 3` e remoção de `thumbnail_url` e campos de LLM/scraping) e `CandidatoMidiaBeta`, introduzindo `ArquivoCuradoriaBetas` (`ONEOF_CONTEUDO` em `Croqui.curadoria_betas` salvo em `curadoria_betas.md`) indexado por `escalada_uid` com `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados`.
- `media-scraping`: Adição do extrator de páginas de blog com recorte de janela de contexto textual, deduplicação contra as 4 listas da escalada (incluindo `betas_rejeitados`) e resolução de preview estilo WhatsApp (YouTube ID + OpenGraph `og:image`) com cache offline persistente.
- `curation-panel`: Integração da aba **Betas** e do atalho na ficha da `Escalada` com `CroquiModel` e `CroquiController` (Undo/Redo), Wizard **"Coletar Betas..."** com barra de progresso, 4 seções expansíveis (`betas_nao_revisados`, `betas_nao_scorados`, `betas`, `betas_rejeitados`) e curadoria estritamente 1 a 1.
- `avaliador-betas-subagente`: Substituição do fluxo baseado em arquivos YAML soltos por skill Antigravity operando sobre o Editor via MCP para avaliar `betas_nao_scorados` com sub-agentes `AvaliadorBetas` e promovê-los a `betas_nao_revisados`.
- `beta-health-check`: Verificação de pendências em `curadoria_betas.md` (`betas_nao_scorados` e `betas_nao_revisados`) com emissão de aviso na compilação (`preparar_submissao_lib.py`), relatório em `STATUS_CROQUIS.md` e omissão de `curadoria_betas` no `compilado.binarypb` e `compilado.yaml`.

## Impact

- **`aresta_api/proto/`**: `beta.proto`, `croqui.proto` e artefatos gerados (`*_pb2.py`, `*.pb.dart`).
- **`coleta_de_betas/`**: Refatoração dos extratores (`youtube.py`, `duckduckgo.py`, `vertex.py`, novo `blog.py`), provedor de preview/cache de imagens (`provedor_imagem_beta.py`), wizard de coleta e `PainelCuradoria`. Remoção dos scripts/módulos legados baseados em `vias_extraidas.yaml` / `betas_pendentes.binarypb`.
- **`editor/`**: `CroquiModel` (carregamento e salvamento de `ArquivoCuradoriaBetas` em `curadoria_betas.md`), `CroquiController` (comandos de transição entre as 4 listas de betas com Undo/Redo), `WidgetEditorDados` (card de resumo de betas e botão *"Abrir na Revisão de Betas"* na `Escalada`) e `JanelaPrincipal` (`PaginaBetas` visível e conectada).
- **`scripts/`**: `preparar_submissao_lib.py` (warning de betas pendentes e limpeza de `curadoria_betas` no binário compilado) e `medir_saude_croquis.py`.
- **`.agents/skills/`**: Nova skill para avaliação de `betas_nao_scorados` via MCP e sub-agentes `AvaliadorBetas`.
