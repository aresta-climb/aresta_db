# Tasks

## 1. Testes Automatizados de Reprodução e Regressão (TDD)

- [x] 1.1 Criar testes unitários em `editor/views/widget_editor_mapas_test.py` reproduzindo a troca de mapa durante `modo_desenho` e verificando ausência de `RuntimeError` no próximo clique
- [x] 1.2 Criar testes unitários em `editor/views/widget_editor_mapas_test.py` para recarregamento de cena (`carregar_mapa`, `_renderizar_mapa`, `descarregar_mapa`) durante `modo_nova_rota` e `modo_conversao`
- [x] 1.3 Criar testes unitários verificando que `cancelar_modo_desenho` e `cancelar_modo_nova_rota` não lançam exceção quando os itens gráficos já tiverem sofrido `cena.clear()`

## 2. Implementação do Cancelamento Seguro e Proteção Defensiva

- [x] 2.1 Implementar método auxiliar `_remover_item_seguro` em `editor/views/widget_editor_mapas.py` utilizando `shiboken6.isValid()` para remoção segura de itens da cena gráfica
- [x] 2.2 Refatorar `cancelar_modo_desenho` e `cancelar_modo_nova_rota` para utilizar `_remover_item_seguro` e limpar referências temporárias
- [x] 2.3 Implementar método centralizado `cancelar_modos_interativos` em `WidgetEditorMapas` e conectá-lo a `set_mapa_atual`, `descarregar_mapa`, `_renderizar_mapa` e inícios de novos modos
- [x] 2.4 Adicionar guardas de integridade em `adicionar_ponto_desenho`, `adicionar_ponto_nova_rota` e `mouseMoveEvent` para recuperação graciosa caso o item temporário esteja invalidado em C++

## 3. Verificação de Cobertura e Integração

- [x] 3.1 Executar a suíte de testes de `widget_editor_mapas_test.py` garantindo 100% de aprovação
- [x] 3.2 Executar os testes de regressão de integração de mapas (`editor/views/jornada_rotas_integracao_test.py`) garantindo conformidade total
