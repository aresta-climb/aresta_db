## 1. Camada Topológica e Lógica Pura (Library-First)

- [ ] 1.1 Criar testes unitários em `editor/core/topologia_trajeto_test.py` para a função `descobrir_caminhos_confluencia` cobrindo snap em nó intermediário, snap em ponto de curva, múltiplas rotas divergentes adiante e snap em nó de topo final.
- [ ] 1.2 Implementar a dataclass `OpcaoCaminhoConfluencia` e a função pura `descobrir_caminhos_confluencia` em `editor/core/topologia_trajeto.py` garantindo aprovação de todos os testes unitários.
- [ ] 1.3 Implementar e testar em `topologia_trajeto_test.py` a resolução de coordenadas contíguas para caminhos compostos por múltiplos segmentos em cadeia (`montar_coordenadas_caminho_remanescente`).
- [ ] 1.4 Executar suite de testes de topologia e verificar 100% de cobertura unitária com `pytest --cov=editor.core.topologia_trajeto`.

## 2. Orquestração no Controlador e Transação Atômica de Histórico

- [ ] 2.1 Criar testes unitários em `editor/controllers/mapas_controller_test.py` cobrindo o método `confluir_rota_em_tracado` nos cenários de fatiamento em nó, fatiamento em curva e confluência direta em topo.
- [ ] 2.2 Implementar `confluir_rota_em_tracado` em `editor/controllers/mapas_controller.py` executando o fatiamento topológico, atualização das referências anteriores, criação da referência da nova rota, desambiguação de topos e empacotamento atômico em macro de `QUndoStack`.
- [ ] 2.3 Adicionar testes de reversibilidade completa (Undo e Redo) em `mapas_controller_test.py` assegurando que `desfazer()` restaura as linhas e referências originais sem resíduos.
- [ ] 2.4 Executar suite do controlador e validar aprovação e cobertura completa com `pytest editor/controllers/mapas_controller_test.py`.

## 3. Componente Visual de Popover Contextual

- [ ] 3.1 Criar testes unitários em `editor/views/componentes/popover_confluencia_rota_test.py` validando renderização de opções, atalhos numéricos (`1`, `2`...), eventos de foco/hover emitindo sinais de pré-visualização e fechamento com `Esc`.
- [ ] 3.2 Implementar o widget flutuante `PopoverConfluenciaRota` em `editor/views/componentes/popover_confluencia_rota.py` com suporte a teclado, mouse hover e tema visual do editor.
- [ ] 3.3 Executar testes do componente popover e validar 100% de aprovação e cobertura com `pytest editor/views/componentes/popover_confluencia_rota_test.py`.

## 4. Integração na Cena Gráfica e Modo de Desenho

- [ ] 4.1 Criar testes em `editor/views/widget_editor_mapas_test.py` para os estados de snap com confluência: exibição do popover, confluência direta no topo, cancelamento seguro e renderização do ghost preview.
- [ ] 4.2 Implementar a renderização do Ghost Preview dinâmico (`item_ghost_preview_temp`) em `editor/views/widget_editor_mapas.py` desenhando a spline translúcida em verde e os nós do caminho destacado.
- [ ] 4.3 Integrar o evento de clique em snap magnético no modo de desenho para invocar o popover em nós/curvas intermediárias e executar confluência direta ao clicar em nós de topo.
- [ ] 4.4 Implementar o tratamento de cancelamento seguro (tecla `Esc` ou clique externo fechando o popover sem adicionar nós ao traçado).

## 5. Testes de Integração e Verificação Geral do Sistema

- [ ] 5.1 Criar testes de integração ponta a ponta em `editor/views/jornada_rotas_integracao_test.py` cobrindo o fluxo completo do usuário: desenhar rota, confluir via popover, verificar integridade do modelo Protobuf e desfazer/refazer via histórico.
- [ ] 5.2 Executar a suíte de testes completa do editor (`pytest editor/`) e a checagem de tipos estáticos (`mypy editor/`) garantindo conformidade rigorosa com `AGENTS.md`.
