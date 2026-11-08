# Tasks

## 1. Remoção de `resumo_edicao` no Schema Protobuf e Guardião AST

- [x] 1.1 Escrever testes em `tests/esquema_proto_test.py` e `tests/contrato_campos_deprecados_protobuf_test.py` validando que `CroquiExperimental.resumo_edicao` foi removido (tag `4` reservada) e que o visitante AST detecta usos de `resumo_edicao`, verificando a falha inicial (*Red*) com `uv run pytest tests/esquema_proto_test.py tests/contrato_campos_deprecados_protobuf_test.py`
- [x] 1.2 Remover `string resumo_edicao = 4;` e adicionar `reserved 4;` em `aresta_api/proto/croqui_experimental.proto`, recompilar os módulos gerados (`uv run python aresta_api/build.py`) e validar que `uv run pytest tests/esquema_proto_test.py` passa (*Green*)

## 2. Remoção de `resumo_edicao` no Core (`GerenciadorCroquiExperimental`) e MCP

- [x] 2.1 Atualizar os testes em `editor/core/croqui_experimental_test.py` e `editor/mcp/ferramentas_ciclo_vida_test.py` para validar que `criar_novo_croqui`, `criar_croqui_a_partir_de_oficial` e `aresta_importar_croqui_oficial` não exigem nem gravam `resumo_edicao` no `croqui_experimental.yaml`
- [x] 2.2 Remover o parâmetro `resumo_edicao` e o valor `"Inicialização automática"` de `editor/core/croqui_experimental.py` e `editor/mcp/ferramentas_ciclo_vida.py`, atualizar `.agents/skills/separar_croqui_pdf_em_partes/SKILL.md` e `.agents/workflows/atualizar_croqui_completo.md`, e verificar que `uv run pytest editor/core/croqui_experimental_test.py editor/mcp/ferramentas_ciclo_vida_test.py` passa com 100% de cobertura

## 3. Pré-seleção do Primeiro Item Visível em `DialogoBuscaCroqui`

- [x] 3.1 Escrever testes orientados a comportamento (sem `MagicMock`, usando `GerenciadorCaminhos` real apontando para `tmp_path`) em `editor/legacy_views/dialogo_busca_croqui_test.py` cobrindo: pré-seleção automática do item `0` ao abrir, atualização automática para o primeiro item visível ao filtrar, confirmação via tecla `Enter` no `campo_busca` e desabilitação/limpeza da seleção quando o filtro não encontra resultados (*Red*)
- [x] 3.2 Implementar a seleção automática do primeiro item visível em `carregar_indice()`, `filtrar_lista()` e a checagem de visibilidade em `obter_id_selecionado()` em `editor/legacy_views/dialogo_busca_croqui.py`, verificando 100% de cobertura em `uv run pytest editor/legacy_views/dialogo_busca_croqui_test.py --cov=editor.legacy_views.dialogo_busca_croqui` (*Green*)

## 4. Simplificação da `TelaDeCarregamento` e `WidgetItemHistorico`

- [x] 4.1 Atualizar e refatorar `editor/legacy_views/tela_de_carregamento_test.py` (substituindo `MagicMock`/`patch` de classes internas por `GerenciadorCaminhos` e Fakes determinísticos reais) para verificar que `ao_clicar_oficial` importa diretamente sem `QInputDialog` e que `WidgetItemHistorico` não exibe `label_resumo` (*Red*)
- [x] 4.2 Remover o `QInputDialog.getText` de `TelaDeCarregamento.ao_clicar_oficial`, a leitura de `resumo_edicao` em `carregar_croquis` e o `label_resumo` de `WidgetItemHistorico` em `editor/legacy_views/tela_de_carregamento.py`, verificando que `uv run pytest editor/legacy_views/tela_de_carregamento_test.py tests/contrato_campos_deprecados_protobuf_test.py` passa sem violações (*Green*)
