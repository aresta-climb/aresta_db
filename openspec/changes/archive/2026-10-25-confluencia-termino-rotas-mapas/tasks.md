## 1. Camada Topológica e Lógica Pura (Library-First)

- [x] 1.1 Criar testes comportamentais em `editor/core/topologia_trajeto_test.py` para `descobrir_caminhos_confluencia` cobrindo: snap em nó intermediário, snap em ponto de curva, junção existente entre sublinhas (`indice_no == 0` ou `len - 1` com continuação), múltiplas rotas divergentes adiante, deduplicação de caminhos remanescentes idênticos, linha avulsa sem referência e detecção de topo final real (`eh_topo_final=True`).
- [x] 1.2 Implementar as dataclasses `OpcaoCaminhoConfluencia` e `ResultadoAnaliseConfluencia` e a função pura `descobrir_caminhos_confluencia` em `editor/core/topologia_trajeto.py` operando sobre `uid`, `pontos_uids` e `alvo_uid` até que todos os testes passem.
- [x] 1.3 Executar a suíte de testes de topologia e verificar 100% de cobertura comportamental com `uv run pytest editor/core/topologia_trajeto_test.py --cov=editor.core.topologia_trajeto --cov-report=term-missing`.

## 2. Orquestração no Controlador e Transação Atômica de Histórico

- [x] 2.1 Criar testes comportamentais (sem mocks internos, usando `CroquiModel` e `QUndoStack` reais) em `editor/controllers/mapas_controller_test.py` para o método `confluir_rota_em_tracado` cobrindo: fatiamento em nó intermediário, fatiamento em ponto de curva, reconexão sem fatiamento em junção existente entre sublinhas e confluência direta em topo final.
- [x] 2.2 Implementar `confluir_rota_em_tracado` em `editor/controllers/mapas_controller.py` executando a criação da escalada (se nova), fatiamento condicional da linha alvo, atualização dos `pontos_uids` das referências existentes, criação da linha exclusiva inicial e da nova `Referencia` (`alvo_uid` + `pontos_uids`), aplicação de `desambiguar_topos` e agrupamento em macro de `QUndoStack`.
- [x] 2.3 Adicionar testes de reversibilidade completa (Undo e Redo) em `editor/controllers/mapas_controller_test.py` assegurando que `undo_stack.undo()` e `undo_stack.redo()` restauram e reaplicam todas as linhas, nós e referências sem resíduos.
- [x] 2.4 Executar a suíte de testes do controlador e validar 100% de aprovação e cobertura com `uv run pytest editor/controllers/mapas_controller_test.py --cov=editor.controllers.mapas_controller --cov-report=term-missing`.

## 3. Componente Visual de Popover Contextual

- [x] 3.1 Criar testes comportamentais com `qtbot` em `editor/views/componentes/popover_confluencia_rota_test.py` validando: exibição das opções com a 1ª opção pré-selecionada (emitindo o sinal de preview imediatamente), atalhos numéricos (`1`, `2`...), confirmação com `Enter`, navegação por setas `↑`/`↓` e hover do mouse atualizando o preview, seleção de "Apenas adicionar ponto e continuar desenhando" e cancelamento seguro com `Esc`.
- [x] 3.2 Implementar o widget `PopoverConfluenciaRota` em `editor/views/componentes/popover_confluencia_rota.py` com espelhamento 1:1 de testes e conformidade visual com o editor.
- [x] 3.3 Executar os testes do componente popover e validar 100% de cobertura comportamental com `uv run pytest editor/views/componentes/popover_confluencia_rota_test.py --cov=editor.views.componentes.popover_confluencia_rota --cov-report=term-missing`.

## 4. Integração na Cena Gráfica e Modo de Desenho

- [x] 4.1 Criar testes comportamentais em `editor/views/widget_editor_mapas_test.py` cobrindo: guarda do 1º clique (`len(pontos_nova_rota) == 0` adicionando ponto normalmente sem abrir popover), abertura do popover em clique com snap intermediário, renderização e limpeza segura do Ghost Preview (`item_ghost_preview_temp`), confluência direta sem popover ao clicar no nó de topo final real e cancelamento seguro (`Esc`) sem adicionar nós.
- [x] 4.2 Implementar o gerenciamento seguro do Ghost Preview (`atualizar_ghost_preview_confluencia` e `limpar_ghost_preview_confluencia` com `shiboken6.isValid` e `_remover_item_seguro`) e a integração do clique em snap no `WidgetEditorMapas` em `editor/views/widget_editor_mapas.py`.
- [x] 4.3 Executar os testes de `widget_editor_mapas_test.py` e validar aprovação com `uv run pytest editor/views/widget_editor_mapas_test.py`.

## 5. Testes de Integração e Verificação Geral do Sistema

- [x] 5.1 Adicionar teste de integração ponta a ponta em `editor/views/jornada_rotas_integracao_test.py` exercitando a jornada completa: iniciar nova rota, clicar em ponto de encontro de via existente, visualizar ghost preview no popover, confirmar confluência, verificar estado do Protobuf (`pontos_uids`, `alvo_uid` e topos) e testar `Ctrl+Z` / `Ctrl+Y`.
- [x] 5.2 Executar a suíte de testes relevante do editor, `ruff check` e `mypy` garantindo zero regressões e total conformidade com `AGENTS.md`.
