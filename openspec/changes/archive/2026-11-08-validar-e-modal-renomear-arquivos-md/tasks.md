# Tasks

## 1. Schema Protobuf (`aresta_api`)

- [x] 1.1 Adicionar o valor `NOME_ARQUIVO = 9` no enum `CampoFormatoUi` e anotar os campos de `MetadadosArquivoNoEditor` (`caminho_original` e `dados_json_originais` com `INVISIVEL`; `caminho_novo` com `formato_na_ui = NOME_ARQUIVO` e `texto_na_ui = "Nome do arquivo"`) em `aresta_api/proto/croqui.proto`, recompilar os stubs em `aresta_api/proto/generated/` e verificar que `croqui_pb2.CampoFormatoUi.NOME_ARQUIVO` está disponível via `uv run pytest scripts/test_proto_schema.py` (ou inspeção direta em Python).

## 2. Biblioteca de Validação e Normalização de Nomes de Arquivo (`editor/core/nomes_arquivos.py`) e Modelo (`CroquiModel`)

- [x] 2.1 Escrever os testes unitários orientados a comportamento em `editor/core/nomes_arquivos_test.py` (*Red*) e implementar em `editor/core/nomes_arquivos.py` (*Green*) as funções `normalizar_entrada_nome_arquivo_md`, `validar_nome_arquivo_md` e `garantir_nome_arquivo_md_seguro` (conversão de espaços em `_`, limite `<= 100` caracteres, regex `^[a-z0-9]+(_[a-z0-9]+)*\.md$`, checagem de duplicidade e fallback seguro), verificando 100% de cobertura com `uv run pytest editor/core/nomes_arquivos_test.py --cov=editor.core.nomes_arquivos --cov-fail-under=100`.
- [x] 2.2 Escrever testes em `editor/models/croqui_model_test.py` (*Red*) para extração/serialização de setores, grupos, mapas gerais e botões textuais com `caminho_novo` ou títulos contendo caracteres tóxicos (`:`, `"`, `/`, `<`, `>`, acentos, apenas símbolos) e atualizar `CroquiModel.extrair_arquivos_e_serializar` em `editor/models/croqui_model.py` (*Green*) para usar `garantir_nome_arquivo_md_seguro`, verificando com `uv run pytest editor/models/croqui_model_test.py`.

## 3. Diálogo Modal de Renomeação e Diálogos de Criação (`editor/views/dialogos/`)

- [x] 3.1 Criar `editor/views/dialogos/dialogo_renomear_arquivo_test.py` (*Red*) e implementar `editor/views/dialogos/dialogo_renomear_arquivo.py` (`DialogoRenomearArquivo`) (*Green*) com normalização de espaços para `_`, validação em tempo real via `validar_nome_arquivo_md`, exibição de erro em `lbl_aviso` e bloqueio do botão de confirmação enquanto inválido/vazio/duplicado, verificando 100% de cobertura com `uv run pytest editor/views/dialogos/dialogo_renomear_arquivo_test.py --cov=editor.views.dialogos.dialogo_renomear_arquivo --cov-fail-under=100`.
- [x] 3.2 Atualizar os testes em `editor/views/dialogos/dialogo_criar_botao_test.py` e `editor/views/dialogos/dialogo_criar_setor_ou_grupo_test.py` (*Red*) e aplicar `validar_nome_arquivo_md` em `DialogoCriarBotao` e `DialogoCriarSetorOuGrupo` (*Green*) para recusar nomes de arquivo vazios, com caracteres inválidos ou acima de `100` caracteres, verificando com `uv run pytest editor/views/dialogos/dialogo_criar_botao_test.py editor/views/dialogos/dialogo_criar_setor_ou_grupo_test.py`.

## 4. Componente `WidgetCampoNomeArquivo` e Integração com `ProtobufWidgetFactory` e `WidgetEditorDados`

- [x] 4.1 Criar `editor/views/widget_campo_nome_arquivo_test.py` (*Red*) e implementar `editor/views/widget_campo_nome_arquivo.py` (`WidgetCampoNomeArquivo`) (*Green*) contendo o `QLineEdit` somente-leitura (`readOnly=True`, `property("protobuf_field", "__filename__")`) e o botão `"Modificar..."` que abre `DialogoRenomearArquivo` e emite sinal `nome_alterado(str)`, verificando 100% de cobertura com `uv run pytest editor/views/widget_campo_nome_arquivo_test.py --cov=editor.views.widget_campo_nome_arquivo --cov-fail-under=100`.
- [x] 4.2 Atualizar `editor/views/protobuf_widget_factory_test.py` (*Red*) e `editor/views/protobuf_widget_factory.py` (*Green*) para instanciar `WidgetCampoNomeArquivo` quando `formato_na_ui == CampoFormatoUi.NOME_ARQUIVO`, verificando com `uv run pytest editor/views/protobuf_widget_factory_test.py`.
- [x] 4.3 Atualizar `editor/views/widget_editor_dados.py`, `editor/views/atualizador_ui.py` e seus respectivos testes (`editor/views/widget_editor_dados_test.py` e `editor/views/atualizador_ui_test.py`) para renderizar `WidgetCampoNomeArquivo` em `_render_filename_field`, coletar arquivos existentes do croqui ao abrir o modal `"Modificar..."`, despachar `controller.alterar_metadados_caminho_novo` ao confirmar e sincronizar Undo/Redo, verificando com `uv run pytest editor/views/widget_editor_dados_test.py editor/views/atualizador_ui_test.py`.

## 5. Receitas de Regressão do Robô Caótico (Issues #86 e #87) e Validação Final

- [x] 5.1 Salvar as receitas de reprodução das issues #86 e #87 em `editor/caos/caminhos_regressao/issue_86_seed_4242424242.json` e `editor/caos/caminhos_regressao/issue_87_seed_4242424274.json` e verificar que toda a suíte de regressão passa sem falhas com `uv run pytest editor/caos/regressao_caminhos_test.py`.
- [x] 5.2 Executar `openspec validate validar-e-modal-renomear-arquivos-md` e a suíte de testes dos módulos afetados garantindo zero regressões.
