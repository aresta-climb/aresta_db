## 1. Validador de Referências e Alerta no Deploy (aresta_db)

- [x] 1.1 [TDD] Escrever testes unitários em `scripts/preparar_submissao_lib_test.py` cobrindo a detecção de referências que não possuem nenhum POI com `label` nem linhas com nós de círculo identificador (`CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `FIM_TOP`) com `rotulo` preenchido.
- [x] 1.2 Implementar a validação em `validar_referencias_mapa()` de `scripts/preparar_submissao_lib.py` emitindo a frase exata de aviso ("A referência '{nome}' no Mapa {idx} em {contexto} não possui label ou rótulo em círculo identificador e não exibirá identificador no mapa do aplicativo.") e verificar que os testes passam com `pytest scripts/preparar_submissao_lib_test.py`.
- [x] 1.3 [TDD] Adicionar testes em `scripts/deploy_generated_test.py` verificando que o processo de deploy exibe os avisos de mapa sem abortar a compilação e validar com `pytest scripts/deploy_generated_test.py`.

## 2. Resolvedor Centralizado de Rótulos no Aplicativo Móvel (aresta_app)

- [ ] 2.1 [TDD] Criar arquivo de teste `test/utils/resolvedor_rotulos_referencia_test.dart` em `aresta_app/frontend` com cenários para: caminhos vetoriais com múltiplos nós identificadores ("5-C", "SS-1-TOP"), POIs convencionais com `label`, deduplicação consecutiva e retorno de string vazia sem fallback para IDs de linhas.
- [ ] 2.2 Implementar o utilitário `extrairRotuloReferencia(Mapa mapa, Mapa_Referencia ref)` em `lib/utils/resolvedor_rotulos_referencia.dart` e verificar aprovação com `flutter test test/utils/resolvedor_rotulos_referencia_test.dart`.
- [ ] 2.3 Substituir a lógica duplicada de `getLabelsForRef` em `lib/pages/mapa_interativo.dart` e de `_resolveRouteMapData` em `lib/view_functions/setor_functions.dart` pelo novo utilitário.
- [ ] 2.4 [TDD] Atualizar ou adicionar testes de widget em `test/view_functions/setor_functions_test.dart` e `test/pages/mapa_interativo_test.dart` verificando a exibição correta do badge ("5-C") e a omissão do badge quando não houver rótulos, validando com `flutter test`.

## 3. Preview de Codenome e Inversão de Ordem no Editor de Mapas (aresta_db)

- [ ] 3.1 [TDD] Escrever testes unitários em `editor/views/widget_painel_referencias_test.py` para a extração do preview de codenome e para a ação de inversão de IDs.
- [ ] 3.2 Implementar o cálculo do codenome no editor e adicionar a pílula de preview (`[ 5-C ]` ou `[ ⚠️ Sem rótulo ]`) no `CardReferencia` em `editor/views/widget_painel_referencias.py`.
- [ ] 3.3 Adicionar o botão `[ 🔄 Inverter ]` no `CardReferencia` que empilha comando de alteração de referência na pilha de histórico `QUndoCommand` invertendo `ref.ids`.
- [ ] 3.4 Verificar a reversibilidade total (Undo/Redo) da inversão de IDs no `CardReferencia` executando `pytest editor/views/widget_painel_referencias_test.py`.

## 4. Verificação Ponta a Ponta e Integração

- [ ] 4.1 Executar a suíte completa de testes do `aresta_app` com `flutter test` garantindo integridade e regressão zero.
- [ ] 4.2 Executar a suíte de testes do `aresta_db` com `pytest` assegurando 100% de cobertura.
- [ ] 4.3 Executar `python scripts/deploy_generated.py -t database/br_mg_igarape_pedra_grande` verificando que o aviso é emitido apropriadamente para o mapa de teste e os binários compilados são gerados com sucesso.
