## 1. Biblioteca Autônoma de Resolução de Referências (`referencias_util.py`)

- [ ] 1.1 [TDD] Criar testes unitários em `editor/models/referencias_util_test.py` cobrindo resolução simétrica de `setor_efetivo` e `grupo_efetivo`, referências implícitas e explícitas em mapas de setor, grupo e pico, além de vias de múltiplas enfiadas
- [ ] 1.2 Implementar `editor/models/referencias_util.py` com funções puras `referencia_aponta_para_escalada`, `obter_contexto_escalada` e `buscar_referencias_para_escalada` e verificar aprovação com 100% de cobertura

## 2. Comando Composto Serializável (`CmdMacro`)

- [ ] 2.1 [TDD] Criar testes unitários em `editor/commands/comandos_macro_test.py` validando execução de Redo em ordem, Undo em ordem reversa, propagação de `armar_carregamento_silencioso` e roundtrip de serialização/deserialização com o `GerenciadorDiario`
- [ ] 2.2 Implementar `CmdMacro` em `editor/commands/comandos_protobuf.py` e registrá-lo na factory `deserializar_comando`
- [ ] 2.3 Atualizar `_despachar_sinal` em `editor/core/historico.py` para inspecionar `CmdMacro.comandos` recursivamente e emitir os sinais correspondentes aos subcomandos

## 3. Banimento Arquitetural e Migração de `beginMacro`/`endMacro`

- [ ] 3.1 [TDD] Adicionar verificação de AST em `editor/arquitetura_mvc_test.py` que proíbe chamadas diretas a `beginMacro` e `endMacro` do Qt
- [ ] 3.2 Migrar `iniciar_grupo_undo` e `finalizar_grupo_undo` em `editor/controllers/mapas_controller.py` para construir e despachar instâncias de `CmdMacro`
- [ ] 3.3 Migrar os usos diretos em `editor/views/widget_editor_mapas.py` para despachar `CmdMacro` e verificar aprovação de `pytest editor/arquitetura_mvc_test.py` sem violações

## 4. Comando Atômico `CmdRenomearEscalada`

- [ ] 4.1 [TDD] Criar testes unitários em `editor/commands/comandos_renomear_escalada_test.py` cobrindo alteração do nome da via, atualização atômica de todas as referências correlatas, comportamento de Undo/Redo, roundtrip no `GerenciadorDiario` e mesclagem `mergeWith` com validação de `session_id`
- [ ] 4.2 Implementar `CmdRenomearEscalada` em `editor/commands/comandos_protobuf.py` com registro em `deserializar_comando`

## 5. Integração Transparente na UI e Sessão por Foco

- [ ] 5.1 [TDD] Criar testes em `editor/controllers/croqui_controller_test.py` garantindo que `alterar_primitivo` em campo `nome` de uma mensagem de escalada instancia `CmdRenomearEscalada` com busca automática de referências
- [ ] 5.2 Implementar o roteamento em `CroquiController.alterar_primitivo` e expor `renomear_escalada`
- [ ] 5.3 Integrar o ciclo de `session_id` no campo de nome em `WidgetEditorDados` para delimitar o `mergeWith` estritamente ao período de foco ininterrupto
- [ ] 5.4 [TDD] Criar teste de integração ponta-a-ponta em `editor/views/widget_editor_dados_mapas_test.py` simulando digitação no formulário de dados, verificação de referências de mapa atualizadas em tempo real, Undo único revertendo ambos, e isolamento de nova sessão após desfocar e adicionar nova referência

## 6. Verificação Geral e Cobertura

- [ ] 6.1 Executar a suíte completa de testes do editor (`pytest editor/`) e verificar 100% de aprovação e integridade de cobertura
