# Tasks

## 1. Exceção Customizada e Resolução Tardia em ComandoEditor

- [x] 1.1 Criar testes unitários em `editor/commands/comandos_protobuf_test.py` definindo o comportamento esperado de `MensagemAlvoNaoEncontradaError(LookupError)`, a ordem de resolução com `_msg_cache` e a prevenção de logs de erro em inspeções passivas.
- [x] 1.2 Implementar a classe de exceção `MensagemAlvoNaoEncontradaError(LookupError)` e ajustar o método `_obter_msg()` em `editor/commands/comandos_protobuf.py`, garantindo que os testes passem com 100% de cobertura.

## 2. Silenciamento de Sinais no Histórico e Proteção em _despachar_sinal

- [x] 2.1 Criar testes unitários em `editor/core/historico_test.py` verificando que nenhum sinal de interface (`sinal_campo_alterado`, `sinal_item_adicionado`, etc.) é emitido durante `carregar_diario_salvo`, e que `_despachar_sinal` descarta graciosamente comandos cuja mensagem não pode ser resolvida sem disparar erros com `id(None)`.
- [x] 2.2 Atualizar `_on_index_changed` em `editor/core/historico.py` para suprimir o despacho de sinais quando `self._gravacao_pausada` estiver ativa, e proteger `_despachar_sinal` para descartar comandos com mensagem nula ou alvo não encontrado.

## 3. Verificação e Integração

- [x] 3.1 Executar os testes unitários e de integração de comandos e histórico (`pytest editor/core/historico_test.py editor/commands/comandos_protobuf_test.py`) e verificar que a cobertura de testes permaneça em 100%.
