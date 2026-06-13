## 1. Atualização do Protobuf

- [x] 1.1 Modificar `croqui.proto` para adicionar o enum `MAPA = 6;` no `MensagemFormatoUi.Enum`.
- [x] 1.2 Atualizar a mensagem `Mapa` em `croqui.proto` para incluir a opção `option (aresta.mensagem_formato_na_ui) = MAPA;`.
- [x] 1.3 Rodar a compilação do protobuf (`scripts/compilar_proto.bat` ou equivalente) para gerar o código em Python.

## 2. Refatoração do WidgetEditorMapas (MVC Model/Controller)

- [x] 2.1 Mover `editor_mapas.py` de `legacy_views/` para `views/widget_editor_mapas.py` e renomear os imports adequados no `main.py` e `area_principal.py`.
- [x] 2.2 Eliminar `GerenciadorArquivosMapa` e as dependências de sistema de arquivo, PyYAML e `ListWidget` (sidebar antiga).
- [x] 2.3 **[TDD]** Criar testes unitários em `widget_editor_mapas_test.py` verificando a geração da sidebar a partir de um `CroquiModel` mockado (100% coverage desejado).
- [x] 2.4 Implementar a lógica da nova barra lateral (`QListWidget`) para passar nos testes acima.
- [x] 2.5 **[TDD]** Criar testes unitários assegurando que interações com o `WidgetEditorMapas` invocam os métodos correspondentes do `CroquiController` (`alterar_primitivo`, `alterar_repeated_item`).
- [x] 2.6 Implementar a substituição dos comandos isolados antigos (como `CmdMoverPonto`) pelas invocações do `CroquiController` em resposta a eventos gráficos (`mouseReleaseEvent`).

## 3. Gateway no Editor de Dados

- [x] 3.1 **[TDD]** Criar testes para o `WidgetEditorDados` verificando a interceptação da extensão `mensagem_formato_na_ui = MAPA` no protobuf `Mapa`. O teste deve assegurar que, em vez de mostrar sub-protos (linhas no form), um botão "Abrir no Editor de Mapas" é renderizado.
- [x] 3.2 Implementar a interceptação condicional em `WidgetEditorDados.atualizar_form()`, injetando o botão customizado que emite o sinal para alternar a aba atual para a aba de Mapas.
- [x] 3.3 Configurar o sinal do botão "Abrir no Editor de Mapas" para setar `self.stacked_widget.setCurrentIndex(2)` e delegar ao `WidgetEditorMapas` o foco.

## 4. Testes e Cleanup

- [x] 4.1 **[TDD]** Rodar toda a suite de testes atual do projeto e certificar-se que a cobertura do `editor/views/widget_editor_mapas.py` continue satisfazendo 100% de coverage (ou próximo).
- [x] 4.2 Deletar os arquivos legados (`scripts/editar_mapas.py`, `scripts/editar_mapas_test.py`) pois toda a lógica agora foi internalizada e padronizada.
- [x] 4.3 Auditar manualmente (via CLI/App) o comportamento de abrir um mapa, adicionar um ponto, mover e usar Ctrl+Z para validar a persistência.
