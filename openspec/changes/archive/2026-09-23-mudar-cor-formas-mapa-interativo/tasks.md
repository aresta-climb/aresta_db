## 1. Helper Compartilhado de Cores e Testes Unitários (TDD)

- [x] 1.1 Criar testes unitários para a função `montar_submenu_cores` em `widget_editor_mapas_test.py`, cobrindo listagem da paleta, marcação da cor ativa, ação "Padrão do Sistema" e cor personalizada, verificando a falha inicial via `pytest editor/views/widget_editor_mapas_test.py`
- [x] 1.2 Implementar a função `montar_submenu_cores` em `widget_editor_mapas.py` e refatorar `ItemTrajetoLinha` para utilizá-la, verificando aprovação dos testes unitários
- [x] 1.3 Executar testes existentes de `ItemTrajetoLinha` garantindo que a refatoração do submenu de cores não introduziu regressões

## 2. Renderização Dinâmica e Estilo Visual em BaseItemPOI (TDD)

- [x] 2.1 Criar testes unitários para `atualizar_estilo_visual` e `carregar_de_dict` testando `ItemBoundingCirculo`, `ItemBoundingRetangulo`, `ItemBoundingQuadrado` e `ItemBoundingPoligono` com cores customizadas e com fallback padrão
- [x] 2.2 Implementar `atualizar_estilo_visual` em `BaseItemPOI` aplicando `QPen` sólida de 2px e `QBrush` com transparência (alpha 60), integrando sua chamada no `__init__` e em `carregar_de_dict`
- [x] 2.3 Atualizar as alças de vértice do polígono (`AlcaVertice`) para sincronizarem suas cores com a cor ativa do polígono, verificando aprovação dos testes unitários

## 3. Integração do Menu de Contexto e Undo/Redo para Formas Geométricas (TDD)

- [x] 3.1 Criar testes unitários de clique direito no menu de contexto das formas (`ItemBoundingCirculo`, `ItemBoundingRetangulo`, `ItemBoundingQuadrado`, `ItemBoundingPoligono`), testando seleção de cor da paleta, personalizada e "Padrão do Sistema", além de verificar o histórico de comandos (`QUndoStack`) e reversão via Undo
- [x] 3.2 Implementar os callbacks `_definir_cor`, `_solicitar_cor_personalizada` e `_definir_cor_padrao` em `BaseItemPOI`, integrando a chamada a `montar_submenu_cores` no `tratar_menu_contexto` com suporte a `registrar_movimento_final`
- [x] 3.3 Padronizar o menu de contexto de `ItemBoundingPoligono` para utilizar a infraestrutura comum, eliminando duplicações e assegurando registro de Undo/Redo
- [x] 3.4 Conectar a alteração de cor realizada no `DialogoEdicaoPOI` para que chame `atualizar_estilo_visual` e reflita imediatamente no canvas

## 4. Verificação de Cobertura e Regressão

- [x] 4.1 Executar a suíte de testes completa `pytest editor/views/widget_editor_mapas_test.py editor/controllers/mapas_controller_test.py` assegurando 100% de aprovação e integridade de todas as geometrias do mapa

