# Proposal

## Why

Ao importar um croqui oficial de produção no Editor Aresta, o fluxo atual interrompe o usuário com um diálogo modal extra (`QInputDialog`) perguntando *"O que você pretende editar em '<id_oficial>'? (Opcional):"* e exige clicar manualmente no item filtrado na lista de busca antes de confirmar. Além disso, o campo `resumo_edicao` resultante gera código e estado desnecessários (como o texto fixo `"Inicialização automática"` em croquis novos e subtítulos redundantes nos cards de histórico), adicionando fricção a uma ação frequente que deveria ser concluída apenas digitando o filtro e pressionando `Enter`.

## What Changes

- **Pré-seleção automática no `DialogoBuscaCroqui`**:
  - Selecionar automaticamente o primeiro item visível da lista ao carregar o índice de croquis oficiais e a cada atualização do filtro de busca.
  - Limpar a seleção e desabilitar o botão `Confirmar` quando nenhum item corresponder ao filtro, garantindo que pressionar `Enter` no campo de busca confirme imediatamente o primeiro croqui visível sem precisar clicar na lista.
- **Remoção do prompt de resumo de edição e limpeza de código morto (`resumo_edicao`)**:
  - Remover o `QInputDialog` de *"Resumo da Edição"* em `TelaDeCarregamento.ao_clicar_oficial`, iniciando a importação imediatamente após a confirmação no `DialogoBuscaCroqui`.
  - Remover a exibição de `label_resumo` no `WidgetItemHistorico` e a leitura de `resumo_edicao` em `TelaDeCarregamento.carregar_croquis`.
  - Remover o parâmetro `resumo_edicao` e o preenchimento fixo `"Inicialização automática"` em `GerenciadorCroquiExperimental` (`_criar_estrutura_croqui`, `criar_novo_croqui` e `criar_croqui_a_partir_de_oficial`).
  - Remover o parâmetro `resumo_edicao` da ferramenta MCP `aresta_importar_croqui_oficial` e das instruções de skills/workflows.
  - **BREAKING (Schema Protobuf interno)**: Remover o campo `resumo_edicao` de `aresta_api/proto/croqui_experimental.proto` reservando a tag `4` (`reserved 4;` no final da mensagem), recompilar os stubs Protobuf e estender o guardião AST (`tests/contrato_campos_deprecados_protobuf_test.py`) para proibir seu uso no código.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability precisa ser criada; as alterações evoluem capabilities existentes. -->

### Modified Capabilities
- `selecao-croqui-oficial`: Atualiza o requisito do `DialogoBuscaCroqui` para pré-selecionar automaticamente o primeiro item visível ao abrir e ao filtrar, permitindo confirmação direta com `Enter`, e iniciar a importação oficial sem prompt intermediário de resumo de edição.
- `croqui-experimental-format`: Atualiza os metadados de `CroquiExperimental` para remover o campo `resumo_edicao` (`reserved 4;`) e deixar de gravá-lo ou exibi-lo na criação, importação e listagem de croquis experimentais.

## Impact

- **Protobuf e Contratos (`aresta_api/` e `tests/`)**:
  - `aresta_api/proto/croqui_experimental.proto` (remoção de `resumo_edicao = 4` com `reserved 4;` e regeneração de `croqui_experimental_pb2.py` / `.pyi`).
  - `tests/esquema_proto_test.py` e `tests/contrato_campos_deprecados_protobuf_test.py`.
- **Core e MCP do Editor (`editor/core/` e `editor/mcp/`)**:
  - `editor/core/croqui_experimental.py` e `editor/core/croqui_experimental_test.py`.
  - `editor/mcp/ferramentas_ciclo_vida.py` e `editor/mcp/ferramentas_ciclo_vida_test.py`.
- **Interface Gráfica do Editor (`editor/legacy_views/`)**:
  - `editor/legacy_views/dialogo_busca_croqui.py` e `editor/legacy_views/dialogo_busca_croqui_test.py`.
  - `editor/legacy_views/tela_de_carregamento.py` e `editor/legacy_views/tela_de_carregamento_test.py` (incluindo refatoração de mocks legados nos testes tocados em conformidade com os Princípios V e VII do `AGENTS.md`).
- **Skills e Workflows de Agentes (`.agents/`)**:
  - `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` e `.agents/workflows/atualizar_croqui_completo.md`.
