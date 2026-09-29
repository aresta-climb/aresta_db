## 1. Testes Unitários de Seleção e Navegação no Editor de Mapas (TDD)

- [x] 1.1 Criar teste unitário em `editor/views/widget_editor_mapas_test.py` verificando que a seleção de mapa de escalada em setor com mapas próprios não é revertida para o mapa do setor e mantém o item correto destacado.
- [x] 1.2 Criar teste unitário em `editor/views/widget_editor_mapas_test.py` simulando a navegação por teclado (tecla de seta para baixo) passando sequencialmente por mapa do setor, mapas de escalada e próximo setor sem loops de seleção.
- [x] 1.3 Criar teste unitário em `editor/views/widget_editor_mapas_test.py` verificando que `scrollToItem` é invocado quando um mapa é selecionado via `selecionar_mapa_por_indices`.

## 2. Implementação no WidgetEditorMapas

- [x] 2.1 Adicionar atributos de estado `self.e_idx` e `self.tipo` em `WidgetEditorMapas` e atualizar `set_mapa_atual` para recebê-los e armazená-los.
- [x] 2.2 Atualizar `_on_mapa_selecionado` para desempacotar `e_idx` e repassá-lo junto com `tipo` na chamada a `set_mapa_atual`.
- [x] 2.3 Refatorar `selecionar_mapa_por_indices` para aceitar `e_idx` e `tipo`, implementando casamento estrito contra as tuplas de `Qt.ItemDataRole.UserRole` e chamando `self.list_widget.scrollToItem(item)`.
- [x] 2.4 Atualizar `_renderizar_mapa` e `_atualizar_lista_mapas` para repassar `e_idx` e `tipo` ao sincronizar a seleção, evitando alterações desnecessárias se o item atual já estiver selecionado.
- [x] 2.5 Atualizar a geração da URI de contexto em `set_mapa_atual` para incluir `expando:escaladas/item:{e_idx}` para mapas de escalada em `mapas_controller.set_contexto`.
- [x] 2.6 Executar os testes da unidade do editor de mapas (`pytest editor/views/widget_editor_mapas_test.py`) e garantir que todos passam.

## 3. Roteamento de Foco Global em area_principal.py (TDD)

- [x] 3.1 Criar testes em `editor/legacy_views/area_principal_test.py` para `_on_foco_requisitado` com URIs de mapas de escalada (em setores diretos e em sub-setores de grupos) e busca por `ctx.arquivo_mapa`.
- [x] 3.2 Atualizar as expressões regulares de extração de caminho em `area_principal._on_foco_requisitado` para capturar `e_idx` antes dos padrões de setor e repassar à chamada `editor.selecionar_mapa_por_indices`.
- [x] 3.3 Expandir a busca de `ctx.arquivo_mapa` em `area_principal.py` para cobrir mapas de escalada.
- [x] 3.4 Executar os testes de `area_principal_test.py` e garantir que passem com sucesso.

## 4. Validação Geral e Cobertura 100%

- [x] 4.1 Executar a suíte de testes relevante com cobertura (`pytest --cov=editor.views.widget_editor_mapas --cov=editor.legacy_views.area_principal`) garantindo 100% de cobertura nos trechos modificados.
- [x] 4.2 Validar conformidade das especificações com `openspec validate`.
