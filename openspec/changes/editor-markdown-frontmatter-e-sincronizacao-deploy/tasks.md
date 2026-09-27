## 1. Ocultação e Preservação de Frontmatter no Markdown

- [x] 1.1 Criar testes unitários em `editor/models/croqui_model_test.py` verificando a extração do frontmatter de `ArquivoMarkdown` para metadados ao carregar e sua recomposição ao serializar
- [x] 1.2 Implementar em `CroquiModel.carregar_arquivos_externos` e `extrair_arquivos_e_serializar` a separação de frontmatter e recomposição em disco, garantindo que os testes passem
- [x] 1.3 Criar testes unitários em `editor/views/widget_editor_dados_test.py` verificando que `WidgetEditorMarkdown` exibe e edita texto sem delimitadores `---` e que o preview funciona de forma direta
- [x] 1.4 Ajustar `WidgetEditorMarkdown` para remover o tratamento manual de `split("---")` no preview e garantir renderização direta do Markdown limpo

## 2. Validação e Avisos de Imagens Ausentes no Deploy

- [x] 2.1 Criar testes unitários em `scripts/deploy_generated_test.py` para a detecção de imagens inexistentes em mapas e markdowns
- [x] 2.2 Implementar `verificar_imagens_inexistentes` em `scripts/deploy_generated.py`, integrando-a ao Passo A da compilação e verificando a passagem dos testes
- [x] 2.3 Validar que links externos (`http://` e `https://`) são devidamente ignorados sem emitir falsos positivos

## 3. Detecção de Modificações no Database e Propagação

- [x] 3.1 Criar testes unitários em `scripts/preparar_submissao_lib_test.py` validando que `corrigir_database` retorna booleano indicando se modificou arquivos no disco
- [x] 3.2 Implementar retorno de flag `modificou_database: bool` em `corrigir_database` e propagá-la através do retorno de compilação em `scripts/deploy_generated.py`
- [x] 3.3 Atualizar `LocalRepoWorkspace` e `ExperimentalWorkspace` em `editor/core/workspace.py` e `TarefaSalvamento` em `editor/core/worker.py` para propagar a indicação de alteração no sinal `sucesso`

## 4. Recarregamento Condicional da Interface no Editor

- [x] 4.1 Criar testes de integração em `editor/legacy_views/area_principal_test.py` cobrindo o fluxo de salvamento: sem reload quando não há alterações no database e com reload e preservação de seleção quando o database é alterado
- [x] 4.2 Implementar método de recarga condicional `_recarregar_dados_apos_salvamento` em `area_principal.py` conectado ao `_on_salvar_sucesso`
- [x] 4.3 Garantir que o item ativo da árvore (`tree_view`) e o formulário em edição sejam restaurados após o recarregamento

## 5. Validação e Testes Finais de Cobertura

- [x] 5.1 Executar a suíte de testes com cobertura (`pytest`) cobrindo todos os módulos alterados para assegurar 100% de cobertura
- [x] 5.2 Executar validação de cabeçalhos e licenças (`scripts/validador_cabecalhos.py`) garantindo conformidade total

