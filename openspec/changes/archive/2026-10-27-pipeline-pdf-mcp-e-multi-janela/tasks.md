# Tasks

## 1. Dependências e Remoção de Scripts Legados de OCR/Mapas

- [x] 1.1 Atualizar `pyproject.toml` movendo `pymupdf` para o grupo de dependências `editor` e removendo `paddleocr`, `paddleocr[doc-parser]` e `paddleocr[ie]` do grupo `pdf`, verificando com `uv sync --group editor` que o ambiente sincroniza sem erros
- [x] 1.2 Remover os scripts legados `scripts/preparar_extracao_de_mapas.py`, `scripts/preparar_extracao_de_mapas_test.py`, `scripts/visualizar_mapa_processado.py`, `scripts/visualizar_mapa_processado_test.py`, `scripts/finalizar_mapas.py`, `scripts/finalizar_mapas_test.py` e `scripts/extrair_ocr_lote.py`, verificando com `uv run pytest scripts/` que a suíte de testes de scripts passa integralmente

## 2. Substituição Declarativa de Listas `repeated` e Remoção de Undo/Redo do MCP

- [x] 2.1 Evoluir `CroquiController.alterar_campo` (`editor/controllers/croqui_controller.py`) para aceitar listas em campos `repeated` (tanto via `campo` + `valor: list` quanto dentro de `campos: dict`), realizando a substituição declarativa (`CmdRemoverRepeated` + `CmdAdicionarRepeated`) dentro de um único `CmdMacro`, preservando `uid`s fornecidos e gerando NanoIDs para novos itens (incluindo sub-listas aninhadas), e verificar que os novos testes de comportamento em `editor/controllers/croqui_controller_test.py` passam com 100% de cobertura
- [x] 2.2 Atualizar `aresta_alterar_campo` em `editor/mcp/ferramentas_comandos.py` para suportar payloads de listas `repeated` e subárvores aninhadas, remover `aresta_desfazer` e `aresta_refazer` de `editor/mcp/ferramentas_ciclo_vida.py`, e verificar com `uv run pytest editor/mcp/ferramentas_comandos_test.py editor/mcp/ferramentas_ciclo_vida_test.py` que a substituição atômica funciona e que `aresta_desfazer`/`aresta_refazer` não constam mais no catálogo MCP

## 3. Trava por Croqui, Registro Multi-Sessão e Roteamento Proxy MCP

- [x] 3.1 Refatorar `editor/core/instancia_unica.py` e `editor/core/gerenciador_git.py` para permitir travas de instância escopadas por croqui (`ArestaEditorCroqui_<id_croqui>`) e lockfile para operações Git compartilhadas, verificando com `uv run pytest editor/core/instancia_unica_test.py editor/core/gerenciador_git_test.py` que croquis distintos podem ser abertos simultaneamente enquanto o mesmo croqui aciona a elevação da janela existente
- [x] 3.2 Evoluir `editor/mcp/sessao.py` e `editor/mcp/servidor.py` para manter o registro multi-sessão (`mcp_sessoes.json`), suportar blocos intercalados arbitrários em `ResultadoFerramenta`, aplicar a guarda defensiva quando nenhum croqui estiver aberto e rotear chamadas da porta primária `27378` por `id_croqui` (localmente ou via proxy HTTP para portas secundárias `27379+`), verificando com `uv run pytest editor/mcp/sessao_test.py editor/mcp/servidor_test.py`

## 4. MCP Ativo na Tela de Carregamento e Ferramentas de Gestão de Croquis e PDF

- [x] 4.1 Implementar em `editor/mcp/ferramentas_ciclo_vida.py` as ferramentas `aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui` e `aresta_particionar_pdf_croqui` (integrada a `repartir_pdf` e pré-alocando esqueletos de `Botao`/`Setor`/`Grupo`/`ColecaoDeMapas` com `UID`s NanoID preservados em atualizações), verificando com `uv run pytest editor/mcp/ferramentas_ciclo_vida_test.py`
- [x] 4.2 Atualizar `editor/main.py` (`ControladorAplicativo`) e `editor/legacy_views/tela_de_carregamento.py` para iniciar o `ServidorMCP` logo no boot do aplicativo, adicionar o botão `"Conectar Agente de IA (MCP)..."` na `TelaDeCarregamento` e suportar abertura de croquis em janela atual (quando na tela inicial) ou em nova janela independente (quando outro croqui já está aberto), verificando com `uv run pytest editor/main_test.py editor/legacy_views/tela_de_carregamento_test.py`

## 5. Renderização de Mapas com Grade Métrica e Recortes de POIs (`aresta_renderizar_mapa`)

- [x] 5.1 Criar o módulo `editor/mcp/renderizador_mapa_mcp.py` (e `editor/mcp/renderizador_mapa_mcp_test.py`) para gerar a imagem completa do mapa com grade métrica semitransparente (`100px`), réguas graduadas nas bordas (`X`/`Y`) e POIs em vermelho, além dos recortes ampliados (`120x120px` escalados) centrados em cada POI com mira `(0, 0)` e réguas relativas (`-50px` a `+50px`), verificando com `uv run pytest editor/mcp/renderizador_mapa_mcp_test.py` que a cobertura do módulo é de 100%
- [x] 5.2 Registrar a ferramenta `aresta_renderizar_mapa` em `editor/mcp/ferramentas_visao.py` retornando a lista intercalada de blocos `[Texto, Imagem]` (metadados + candidatos vetoriais `PyMuPDF` + visão geral com grade + pares `[Texto do POI, Recorte com mira relativa]`), verificando com `uv run pytest editor/mcp/ferramentas_visao_test.py`

## 6. Reescrita das Skills, Workflows e Documentação MCP

- [x] 6.1 Reescrever `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md`, `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md` e `.agents/skills/preencher_croqui_yaml/SKILL.md` para operarem 100% via ferramentas MCP (`aresta_listar_croquis`, `aresta_criar_novo_croqui`, `aresta_importar_croqui_oficial`, `aresta_particionar_pdf_croqui`, `aresta_alterar_campo`, `aresta_compilar`, `aresta_salvar`) sem criação ou edição manual de arquivos `.md` ou `croqui.yaml`, verificando que `aresta_listar_skills` e `aresta_ler_skill` servem o conteúdo atualizado
- [x] 6.2 Reescrever `.agents/skills/mapa_extrair_pontos_de_interesse/SKILL.md`, `.agents/skills/mapa_corrigir_pontos_de_interesse/SKILL.md`, `.agents/workflows/processar_croqui_completo.md`, `.agents/workflows/atualizar_croqui_completo.md` e `docs/mcp.md` para utilizarem `aresta_renderizar_mapa` e `aresta_alterar_campo` (sem `PaddleOCR` nem scripts legados), verificando com `uv run pytest editor/mcp/` que todos os testes da camada MCP passam
