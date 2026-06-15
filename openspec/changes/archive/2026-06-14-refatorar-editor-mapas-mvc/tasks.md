## 1. Arquitetura Base e Comandos (TDD)

- [x] 1.1 Criar `editor/commands/comandos_mapas_test.py` com testes falhos para os novos comandos.
- [x] 1.2 Criar `editor/commands/comandos_mapas.py` para fazer os testes passarem.
- [x] 1.3 Extrair `CmdMoverPonto` e afins do `widget_editor_mapas.py` para `comandos_mapas.py`, mantendo 100% coverage.
- [x] 1.4 Refatorar `CmdMoverPonto` para atuar nas interfaces do `CroquiModel` em vez de manipular YAML/dicionários.
- [x] 1.5 Deletar `editor/core/mapas_lib.py` (e seus respectivos testes, se existirem).

## 2. Controllers (TDD)

- [x] 2.1 Criar `editor/controllers/mapas_controller_test.py` definindo o comportamento esperado das delegações.
- [x] 2.2 Criar `editor/controllers/mapas_controller.py`.
- [x] 2.3 Implementar inicialização com `CroquiModel` e `QUndoStack` (comprovado pelos testes).
- [x] 2.4 Mover a função utilitária `converter_box_para_circulo` para dentro de `MapasController` e portar seus testes.
- [x] 2.5 Implementar métodos de delegação: `adicionar_poi`, `mover_poi`, `deletar_poi`, `obter_caminho_imagem_mapa`, buscando 100% de coverage.

## 3. View e Integração

- [x] 3.1 Em `editor/views/widget_editor_dados.py`, instanciar `MapasController` e passar para a inicialização do `WidgetEditorMapas`.
- [x] 3.2 Limpar propriedades de estado legado (arquivos, YAML) em `WidgetEditorMapas`.
- [x] 3.3 Implementar método `set_mapa_atual(msg_mapa, pico_idx, grupo_idx, mapa_idx)` no widget para receber o contexto do mapa.
- [x] 3.4 Implementar rastreamento granular com dicionário `idx_poi -> QGraphicsItem` na View.
- [x] 3.5 Conectar a view aos sinais do `CroquiModel` (`repeated_item_alterado`, `repeated_adicionado`, `repeated_removido`) implementando o ajuste sequencial de índices.
- [x] 3.6 Refatorar menu de contexto e drag-and-drop para despachar intenções via `self.mapas_controller`.

## 4. Testes e Regras

- [x] 4.1 Modificar `editor/arquitetura_mvc_test.py` para proibir qualquer `QUndoCommand` fora do diretório `commands/` e arquivos de teste.
- [x] 4.2 Atualizar `editor/views/widget_editor_mapas_test.py` para refletir o novo ciclo de vida focado em Protobuf e Controller (sem Mocks de disco/YAML).
