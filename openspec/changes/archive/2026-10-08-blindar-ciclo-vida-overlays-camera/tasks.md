# Tasks

## 1. Testes de Ciclo de Vida e Reprodução de Falhas (TDD)

- [x] 1.1 Adicionar testes unitários em `editor/views/widget_editor_mapas_test.py` simulando destaque de POIs com câmera (`destacar_pois_temporariamente`) seguido de limpeza de cena (`cena.clear()`), verificando que um novo destaque (com câmera ou sem câmera) e remoção de destaque não lancem exceção do Shiboken.
- [x] 1.2 Adicionar testes unitários em `editor/views/widget_editor_mapas_test.py` para `iniciar_modo_camera` após limpeza ou troca de cena, garantindo que o overlay de modo câmera seja re-instanciado com segurança sem desreferenciar ponteiros C++ mortos.

## 2. Implementação da Blindagem de Ciclo de Vida dos Overlays

- [x] 2.1 Implementar método auxiliar `_item_grafico_valido(self, item: Any, cena_esperada: Optional[Any] = None) -> bool` em `WidgetEditorMapas` para inspecionar validade em C++ (`shiboken6.isValid`) e pertinência à cena gráfica.
- [x] 2.2 Atualizar `cancelar_modos_interativos`, `descarregar_mapa`, `set_mapa_atual` e `_renderizar_mapa` em `editor/views/widget_editor_mapas.py` para limpar e anular proativamente `item_hover_camera_overlay` e `item_camera_overlay`.
- [x] 2.3 Atualizar `destacar_pois_temporariamente` e `iniciar_modo_camera` para utilizar `_item_grafico_valido`, re-instanciando transparentemente novos itens gráficos quando a instância anterior for inválida ou divergir da cena atual.
- [x] 2.4 Rodar os testes de `widget_editor_mapas_test.py` e verificar que todas as asserções passam verde.

## 3. Validação de Cobertura e Integridade

- [x] 3.1 Executar os testes de unidade com relatório de cobertura (`uv run pytest editor/views/widget_editor_mapas_test.py --cov=editor.views.widget_editor_mapas --cov-report=term-missing`) e garantir 100% de cobertura nos ramos alterados.
- [x] 3.2 Executar a suíte de testes do editor (`uv run pytest editor/`) validando ausência de regressões em outros componentes.
