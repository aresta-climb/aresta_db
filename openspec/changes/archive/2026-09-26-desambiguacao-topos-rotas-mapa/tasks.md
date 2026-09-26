## 1. Testes Unitários e Especificação (TDD)

- [x] 1.1 Escrever testes unitários em `editor/core/topologia_trajeto_test.py` cobrindo múltiplas rotas isoladas no mesmo mapa, verificando que nenhuma recebe letra no topo e todas mantêm o último nó como `PASSAGEM` com rótulo vazio.
- [x] 1.2 Escrever testes unitários em `editor/core/topologia_trajeto_test.py` cobrindo cenários mistos (rotas isoladas coexistindo com rotas bifurcadas e rotas convergentes), validando que apenas os topos ambíguos recebem letras sequenciais ('A', 'B'...).
- [x] 1.3 Escrever testes unitários em `editor/core/topologia_trajeto_test.py` cobrindo a restauração de nó limpo quando uma rota volta a ser isolada após a remoção de sua variante.

## 2. Implementação do Motor de Desambiguação Topológica

- [x] 2.1 Refatorar `desambiguar_topos` em `editor/core/topologia_trajeto.py` para inspecionar conectividade relacional (início, fim, nós e linhas) e identificar `compartilha_fim` e `tem_bifurcacao`.
- [x] 2.2 Implementar atribuição de letras sequenciais exclusivamente para topos com desambiguação requerida e redefinição dos topos isolados para `PASSAGEM` sem rótulo textual.
- [x] 2.3 Executar `pytest editor/core/topologia_trajeto_test.py` e garantir 100% de aprovação e cobertura unitária.

## 3. Testes de Integração e Validação de Histórico (Undo/Redo)

- [x] 3.1 Adicionar teste em `editor/controllers/mapas_controller_test.py` validando que `adicionar_rota_com_tracado` com múltiplas rotas isoladas preserva topos limpos e reverte adequadamente no histórico (`QUndoStack`).
- [x] 3.2 Adicionar teste de integração em `editor/views/jornada_rotas_integracao_test.py` verificando o fluxo ponta a ponta na interface gráfica ao adicionar múltiplas rotas isoladas e variantes.
- [x] 3.3 Executar a suíte completa de testes (`pytest editor/`) para garantir regressão zero.
