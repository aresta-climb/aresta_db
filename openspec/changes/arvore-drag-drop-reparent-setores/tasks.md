## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [ ] 1.1 Escrever cenários de teste de integração em `editor/views/widget_editor_dados_test.py` definindo a fronteira de reordenação na mesma lista via arrastar e soltar com verificação de Undo/Redo e sincronização visual.
- [ ] 1.2 Escrever cenários de teste de integração em `editor/views/widget_editor_dados_test.py` para os três casos de migração hierárquica (Pico ➔ Grupo, Grupo ➔ Pico, Grupo A ➔ Grupo B) e respectivo Undo.
- [ ] 1.3 Escrever cenário de teste de integração em `editor/views/widget_editor_dados_test.py` para a fronteira de colisão de arquivos (aborto do drop com diálogo de aviso `QMessageBox.warning` e preservação do estado).

## 2. Biblioteca de Migração e Nomenclatura (Princípio II - Library-First com TDD)

- [ ] 2.1 Criar suite de testes unitários `editor/core/migracao_setor_test.py` cobrindo regras de compatibilidade de movimento, cálculo de caminhos de arquivos e detecção de colisões (Vermelho/Red).
- [ ] 2.2 Implementar biblioteca independente `editor/core/migracao_setor.py` com as funções puras `validar_movimento_permitido`, `calcular_novo_caminho_setor` e `verificar_colisao_nome_arquivo` até aprovação total dos testes (Verde/Green).
- [ ] 2.3 Garantir 100% de cobertura de testes unitários em `editor/core/migracao_setor.py` (Princípio III).

## 3. Comandos de Histórico e Controller (Princípio VII com TDD)

- [ ] 3.1 Escrever testes unitários em `editor/commands/comandos_protobuf_test.py` para o comando atômico `CmdMigrarSetor` e em `editor/controllers/croqui_controller_test.py` para o método `migrar_setor` (Vermelho/Red).
- [ ] 3.2 Implementar a classe de comando `CmdMigrarSetor` em `editor/commands/comandos_protobuf.py` com `undo()`, `executar_redo()`, `serializar()` e `deserializar()`.
- [ ] 3.3 Adicionar método despachador `migrar_setor` em `CroquiController` e método de suporte no `CroquiModel`.
- [ ] 3.4 Garantir 100% de cobertura de testes unitários para `CmdMigrarSetor` (Princípio III).

## 4. Visualização e Interação de Arrastar e Soltar (UI)

- [ ] 4.1 Escrever testes em `editor/views/tree_view_adapter_test.py` para flags de arrastar (`flags`, `supportedDropActions`) e empacotamento de dados MIME.
- [ ] 4.2 Configurar flags de arrastar e soltar no `ProtobufTreeViewAdapter` para itens de Setor e Grupo elegíveis.
- [ ] 4.3 Configurar propriedades de arrastar e soltar na `tree_view` em `WidgetEditorDados` (`setDragEnabled(True)`, `setAcceptDrops(True)`, `setDropIndicatorShown(True)`).
- [ ] 4.4 Implementar interceptação de `dragMoveEvent` em `WidgetEditorDados` integrando com `validar_movimento_permitido` da biblioteca `migracao_setor`.
- [ ] 4.5 Implementar interceptação de `dropEvent` em `WidgetEditorDados` para orquestrar: validação, verificação de colisão com aviso, despacho para o controller (`CmdMoverRepeated` ou `CmdMigrarSetor`), auto-expansão do grupo de destino e restauração de foco/seleção.

## 5. Validação de Princípios, Cobertura Total e Regressão

- [ ] 5.1 Executar os testes de integração do Grupo 1 e certificar-se de que todos passam (Verde/Green).
- [ ] 5.2 Executar a suite completa de testes do editor (`pytest editor/`) garantindo ausência de regressões e 100% de cobertura de testes nos novos módulos.
- [ ] 5.3 Auditar todos os novos arquivos e modificações para assegurar que 100% dos identificadores, funções, variáveis e comentários estejam estritamente em português brasileiro (Princípio I).
