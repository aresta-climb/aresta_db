## 1. Biblioteca de Mapas (Library-First)

- [x] 1.1 Criar `editor/core/mapas_lib.py` com lógica de manipulação de POIs e YAML, extraída de `scripts/editar_mapas.py`.
- [x] 1.2 Criar `editor/core/mapas_lib_test.py` com testes unitários para a lógica de mapas e conversões.

## 2. Refatoração do Editor de Mapas Visual

- [x] 2.1 Criar `editor/views/editor_mapas.py` contendo o `WidgetEditorMapas`, `GraphicsScene` e itens gráficos POI.
- [x] 2.2 Criar `editor/views/editor_mapas_test.py` com testes básicos para o widget e componentes visuais.
- [x] 2.3 Atualizar `scripts/editar_mapas.py` para utilizar o novo `WidgetEditorMapas`, mantendo a funcionalidade original de linha de comando.

## 3. Integração na Janela Principal

- [x] 3.1 Atualizar `PaginaMapas` em `editor/views/area_principal.py` para instanciar e exibir o `WidgetEditorMapas`.
- [x] 3.2 Implementar a lógica de carregamento dos mapas do croqui atual no `WidgetEditorMapas`.
- [x] 3.3 Sincronizar as ações de salvamento e estado de modificação ("dirty") entre o widget de mapas e a janela principal.

## 4. Verificação Final

- [x] 4.1 Realizar testes manuais de edição de POIs dentro da janela principal do editor.
- [x] 4.2 Executar `scripts/editar_mapas_test.py` e garantir que passe com o mínimo de mudanças possível.
- [x] 4.3 Validar a persistência dos dados no arquivo YAML do croqui.
- [x] 4.4 Garantir conformidade com os princípios de "Tudo em Português" e TDD em toda a implementação.
