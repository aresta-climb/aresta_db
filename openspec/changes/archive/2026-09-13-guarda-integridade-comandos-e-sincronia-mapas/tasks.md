## 1. Guarda de Integridade nos Comandos Protobuf (TDD)

- [x] 1.1 Escrever testes unitários em `editor/commands/comandos_protobuf_test.py` cobrindo a rejeição (via `ValueError`) na instanciação de comandos com nós órfãos/desconectados e campos inválidos, além de aceitação de nós conectados válidos e raiz, e verificar que falham inicialmente (Red)
- [x] 1.2 Implementar a função auxiliar de validação de pertinência à árvore e integrá-la no construtor dos comandos Protobuf em `editor/commands/comandos_protobuf.py`, verificando aprovação de todos os testes unitários (Green)
- [x] 1.3 Escrever testes unitários em `editor/core/historico_test.py` e implementar tratamento defensivo no `historico.py` para ignorar comandos órfãos/inválidos durante a deserialização e replay do diário com log de aviso, sem abortar a restauração dos comandos íntegros

## 2. Sincronização Reativa e Guarda no Editor de Mapas (TDD)

- [x] 2.1 Escrever testes unitários em `editor/views/widget_editor_mapas_test.py` cobrindo a remoção e adição reativa de mapas (`campo_nome == 'mapas'`), verificando se a lista lateral é atualizada e se a cena é descarregada caso o mapa ativo seja excluído (Red)
- [x] 2.2 Implementar o tratamento reativo de `campo_nome == 'mapas'` nos métodos `_on_repeated_removido` e `_on_repeated_adicionado` do `WidgetEditorMapas`, verificando a aprovação dos testes (Green)
- [x] 2.3 Escrever testes unitários e implementar o método `_mapa_ativo_valido()` e guardas preventivas nos métodos de inserção e desenho (`adicionar_poi`, `_on_desenho_linha_concluido`, `_on_adicionar_referencia`, etc.) do `WidgetEditorMapas`, abortando operações em mapas desanexados

## 3. Validação Integrada e Cobertura de Testes (100%)

- [x] 3.1 Executar a suíte de testes unitários com cobertura (`pytest --cov`) nos módulos alterados (`comandos_protobuf.py`, `widget_editor_mapas.py`, `historico.py`), assegurando 100% de cobertura e conformidade com os princípios do Aresta
- [x] 3.2 Executar `openspec validate guarda-integridade-comandos-e-sincronia-mapas` garantindo conformidade formal de todos os artefatos da change
