# Proposal: Corrigir Resolução de Mensagens no Diário e Silenciar Sinais no Boot

## Why

Durante a inicialização do Editor Aresta ao abrir um croqui salvo, o sistema restaura o histórico de comandos (`diario_salvo.bin`) para a pilha `QUndoStack` através de `carregar_diario_salvo`. Cada chamada a `_pilha.push(cmd)` dispara o sinal `indexChanged`, fazendo com que `_despachar_sinal` acesse ansiosamente a propriedade `cmd.msg` de cada comando histórico.

Como comandos de sessões anteriores podem referenciar caminhos de entidades que foram excluídas, reordenadas ou migradas antes do salvamento consolidado no disco, a resolução tardia (`navegar_para_mensagem`) falha, emitindo dezenas de `logger.error` em rajada de milissegundos que sobrecarregam o Sentry. Além disso, `_obter_msg()` emite logs de erro críticos genéricos sem tipagem customizada, `_despachar_sinal` tenta emitir sinais de UI com `id(None)`, e a resolução tardia em `_obter_msg()` avalia a navegação antes de verificar o cache de mensagens.

## What Changes

- **Silenciamento de Sinais no Boot e Restauração de Diário**:
  - `GerenciadorHistorico._on_index_changed` passa a verificar se o gerenciador está em modo de carga silenciosa ou gravação pausada (`_gravacao_pausada = True`), suprimindo o despacho de sinais de UI e o acesso ansioso a `cmd.msg` durante `carregar_diario_salvo`.
- **Exceção Customizada de Resolução (`MensagemAlvoNaoEncontradaError`)**:
  - Introdução da exceção customizada `MensagemAlvoNaoEncontradaError(LookupError)` em `editor/commands/comandos_protobuf.py` para tipar especificamente falhas na localização da mensagem alvo na árvore Protobuf.
  - Como herda de `LookupError`, encaixa-se nativamente no tratamento já existente de comandos órfãos/corrompidos descartáveis em `carregar_diario_salvo` e `restaurar_do_diario`.
- **Proteção e Defesa em `_despachar_sinal`**:
  - Antes de emitir qualquer sinal de alteração (`sinal_campo_alterado`, `sinal_item_adicionado`, etc.), valida se `cmd.msg` existe e não é `None`. Se a mensagem alvo não puder ser resolvida ou disparar `MensagemAlvoNaoEncontradaError`, o sinal é descartado de forma segura sem emitir eventos para `id(None)`.
- **Correção da Ordem de Resolução em `_obter_msg()`**:
  - Em `ComandoEditor._obter_msg()`, se `self._msg_cache` estiver disponível e válido, prioriza o objeto cacheado ou captura a falha de navegação com a exceção tipada `MensagemAlvoNaoEncontradaError`, evitando logs indevidos de erro em inspeções passivas.

## Capabilities

### Modified Capabilities
- `editor-diario-recuperacao`: Assegura que o carregamento silencioso do diário salvo (`carregar_diario_salvo`) suprima a emissão de sinais reativos de UI no `QUndoStack` e capture exceções tipadas de resolução sem poluir telemetria ou logs de erro.
- `undo-redo-protobuf`: Formaliza a exceção customizada `MensagemAlvoNaoEncontradaError(LookupError)` para resolução tardia de alvos, protege o despacho de sinais para não disparar eventos com nós nulos, e restringe erros críticos aos momentos de execução real de mutação (`undo()` e `executar_redo()`).

## Impact

- `editor/core/historico.py`: `_on_index_changed` e `_despachar_sinal` atualizados para respeitar `_gravacao_pausada` e tratar `MensagemAlvoNaoEncontradaError`/`None`.
- `editor/commands/comandos_protobuf.py`: Criação de `MensagemAlvoNaoEncontradaError`, ajuste em `_obter_msg()`.
- Testes unitários em `editor/core/historico_test.py` e `editor/commands/comandos_protobuf_test.py` cobrindo o silenciamento no boot, o lançamento e captura da exceção customizada e a prevenção de emissão de sinais com mensagens nulas.
