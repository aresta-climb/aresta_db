# Proposal

## Why

Atualmente, os agentes e *skills* de conversão e atualização de croquis em PDF operam gerando e editando manualmente arquivos intermediários no disco (`.md` com YAML Frontmatter, `croqui.yaml` e JSONs em `raw_mapas/`), além de dependerem do pacote pesado `PaddleOCR` (`paddlepaddle`) e de scripts auxiliares de linha de comando (`preparar_extracao_de_mapas.py`, `visualizar_mapa_processado.py`, `finalizar_mapas.py`). Esse fluxo sofre com erros de sintaxe/indentação YAML, impede a edição de múltiplos croquis em paralelo devido à trava global de instância única do Editor Aresta e exige que um croqui já tenha sido aberto manualmente antes mesmo de o servidor MCP ficar ativo.

Unificar 100% das *skills* e *workflows* de conversão de PDF e extração de mapas no servidor MCP do Editor Aresta — combinado com suporte a múltiplas janelas abertas simultaneamente (com trava por croqui e proxy MCP na porta `27378`), ativação do MCP já na Tela de Carregamento e uma ferramenta visual de renderização de mapas com grade métrica e recortes de zoom (`aresta_renderizar_mapa`) — elimina toda edição manual de arquivos pelos agentes, aposenta a dependência do `PaddleOCR` e garante transações atômicas livres de condições de corrida.

## What Changes

- **Servidor MCP Ativo Desde a Tela de Carregamento e Gestão de Croquis via MCP**:
  - Iniciar o `ServidorMCP` logo na abertura do aplicativo (`ControladorAplicativo` / `TelaDeCarregamento`), adicionando o botão **"Conectar Agente de IA (MCP)..."** diretamente na `TelaDeCarregamento`.
  - Expor novas ferramentas MCP de gestão de croquis:
    - `aresta_listar_croquis`: lista croquis `abertos` (em janelas ativas), `em_andamento` (rascunhos experimentais locais) e `oficiais` (repositório de produção, com filtro `busca`).
    - `aresta_abrir_croqui_existente`: abre um croqui em andamento ou pasta local `database/<id_croqui>`.
    - `aresta_importar_croqui_oficial`: clona um croqui oficial de produção para edição experimental, compila e abre.
    - `aresta_criar_novo_croqui`: inicializa um novo croqui a partir de `nome_pico`, `cidade`, `estado` e `pais` e abre no Editor.
    - `aresta_particionar_pdf_croqui`: executa o particionamento do PDF (`PyMuPDF`), extrai sub-PDFs, imagens `.webp` e sementes vetoriais de texto/desenho, e pré-aloca na árvore Protobuf os esqueletos de `Botao`, `Setor`, `Grupo` e `ColecaoDeMapas` já com `UID`s NanoID (preservando `UID`s existentes em atualizações).
  - Adicionar guarda defensiva global no servidor MCP: quando nenhum croqui estiver aberto, qualquer ferramenta de inspeção ou mutação de croqui retorna erro descritivo orientando o uso de `aresta_listar_croquis` e das ferramentas de abertura/criação.
- **Suporte a Múltiplas Janelas em Paralelo com Trava por Croqui e Proxy MCP na Porta `27378`**:
  - Substituir a trava global de processo único (`ArestaEditorSingleInstanceServer`) por trava por croqui (`ArestaEditorCroqui_<id_croqui>`) e lockfile para operações Git compartilhadas, permitindo abrir múltiplos croquis diferentes em janelas independentes simultaneamente (e trazendo a janela existente para frente caso o mesmo croqui seja solicitado novamente).
  - Evoluir `editor/mcp/sessao.py` e `editor/mcp/servidor.py` para manter um registro multi-sessão (`mcp_sessoes.json`) e rotear transparentemente requisições da porta primária `27378` para as portas secundárias (`27379+`) usando o parâmetro opcional `id_croqui`.
- **Substituição Atômica de Entidades (Incluindo Listas `repeated`) e Remoção de `Undo/Redo` do MCP**:
  - **BREAKING (MCP)**: Remover `aresta_desfazer` e `aresta_refazer` do catálogo de ferramentas MCP (mantendo o `QUndoStack` intacto para uso humano via interface gráfica), impedindo que subagentes paralelos desfaçam operações uns dos outros.
  - Evoluir `CroquiController.alterar_campo` e `aresta_alterar_campo` para aceitar listas completas em campos `repeated` (tanto em `campo` + `valor: list` quanto dentro de `campos: dict`), realizando a substituição declarativa completa da lista (`CmdRemoverRepeated` + `CmdAdicionarRepeated`) agrupada no mesmo `CmdMacro` atômico (preservando `uid`s informados nos itens e gerando NanoIDs para novos itens).
- **Renderização de Mapas com Grade Métrica e Recortes de Zoom (`aresta_renderizar_mapa`) sem `PaddleOCR`**:
  - Mover `pymupdf` para o grupo de dependências `editor` em `pyproject.toml` e **remover** `paddleocr`, `paddleocr[doc-parser]` e `paddleocr[ie]`.
  - Criar a ferramenta MCP `aresta_renderizar_mapa` que retorna uma sequência intercalada de blocos `[Texto, Imagem]`:
    1. Texto descritivo com metadados do mapa (`largura`, `altura`, candidatos vetoriais extraídos via `PyMuPDF`) + Imagem completa do mapa com grade métrica semitransparente (`100px`), réguas graduadas nas bordas (`X`/`Y`) e todos os POIs demarcados em vermelho.
    2. Pares `[Texto, Imagem]` para cada POI cadastrado, onde o texto identifica explicitamente `uid`, `rotulo`, `centro=(x, y)` e `geometria`, seguido do recorte ampliado (`120x120px`) centrado no POI com mira `(0, 0)` e régua relativa de `-50px` a `+50px`.
  - **BREAKING (Scripts)**: Remover os scripts legados `scripts/preparar_extracao_de_mapas.py` (e `_test.py`), `scripts/visualizar_mapa_processado.py` (e `_test.py`), `scripts/finalizar_mapas.py` (e `_test.py`) e `scripts/extrair_ocr_lote.py`.
- **Migração Integral das Skills e Workflows para Operação 100% via MCP**:
  - Reescrever `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md`, `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`, `.agents/skills/preencher_croqui_yaml/SKILL.md`, `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md`, `.agents/skills/mapa_corrigir_pontos_de_interesse/SKILL.md` e os workflows `.agents/workflows/processar_croqui_completo.md` e `.agents/workflows/atualizar_croqui_completo.md` para operarem exclusivamente via ferramentas MCP do Editor Aresta, proibindo edição manual de arquivos `.md`, `.yaml` ou `.json`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade isolada; as capacidades existentes abaixo concentram todos os requisitos. -->

### Modified Capabilities
- `editor-controle-mcp`: Servidor MCP ativo desde a inicialização/Tela de Carregamento, ferramentas de listagem/abertura/criação/particionamento PDF de croquis, guarda de "nenhum croqui aberto", suporte a múltiplas janelas com trava por croqui e roteamento proxy por `id_croqui` na porta `27378`, substituição declarativa de listas `repeated` em `aresta_alterar_campo`, remoção de `aresta_desfazer`/`aresta_refazer` e nova ferramenta `aresta_renderizar_mapa` com sequência intercalada de imagens com grade métrica e recortes de POIs.
- `editor-tela-de-carregamento`: Botão "Conectar Agente de IA (MCP)..." na Tela de Carregamento e transição/abertura de janelas de croquis acionada tanto pela interface quanto pelas ferramentas MCP.
- `agentes-extracao-pdf`: Operação 100% via MCP para particionamento de PDF, conversão de setores/grupos/botões em chamada atômica por `UID`, extração/refinamento de POIs e compilação/salvamento, proibindo criação ou edição manual de arquivos `.md`, `.yaml` e `.json`.
- `workflow-extracao-mapas-escalada`: Substituição do pipeline baseado em `PaddleOCR` e scripts intermediários (`preparar_extracao_de_mapas.py`, `visualizar_mapa_processado.py`, `finalizar_mapas.py`) pela ferramenta MCP `aresta_renderizar_mapa` (com sementes vetoriais `PyMuPDF`, grade métrica e recortes de zoom por POI) e atualização atômica via `aresta_alterar_campo`.

## Impact

- **`pyproject.toml`**: Inclusão de `pymupdf` no grupo `editor`; remoção de `paddleocr`, `paddleocr[doc-parser]` e `paddleocr[ie]` do grupo `pdf`.
- **`editor/core/instancia_unica.py` e `editor/main.py`**: Trava de instância única escopada por croqui, inicialização do `ServidorMCP` no `ControladorAplicativo` antes da abertura de croqui e suporte a abertura de novas janelas para croquis distintos.
- **`editor/legacy_views/tela_de_carregamento.py`**: Botão "Conectar Agente de IA (MCP)..." e integração com o `ControladorAplicativo` para abertura de croquis acionada via MCP.
- **`editor/controllers/croqui_controller.py` e `editor/commands/comandos_protobuf.py`**: Suporte a substituição declarativa de campos `repeated` dentro de `alterar_campo` agrupada em `CmdMacro`.
- **`editor/mcp/` (`sessao.py`, `servidor.py`, `ferramentas_ciclo_vida.py`, `ferramentas_comandos.py`, `ferramentas_visao.py`)**: Registro multi-sessão `mcp_sessoes.json`, proxy por `id_croqui`, guarda de croqui aberto, novas tools de gestão de croquis e PDF (`aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui`, `aresta_particionar_pdf_croqui`), remoção de `aresta_desfazer`/`aresta_refazer` e adição de `aresta_renderizar_mapa`.
- **`scripts/`**: Remoção de `preparar_extracao_de_mapas.py`, `preparar_extracao_de_mapas_test.py`, `visualizar_mapa_processado.py`, `visualizar_mapa_processado_test.py`, `finalizar_mapas.py`, `finalizar_mapas_test.py` e `extrair_ocr_lote.py`.
- **`.agents/skills/` e `.agents/workflows/` e `docs/mcp.md`**: Atualização completa para o fluxo 100% MCP.
