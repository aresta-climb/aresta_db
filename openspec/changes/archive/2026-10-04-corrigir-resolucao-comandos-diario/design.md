# Design: Corrigir Resolução de Mensagens no Diário e Silenciar Sinais no Boot

## Context

Conforme detalhado no `proposal.md`, ao inicializar o Editor Aresta e carregar um croqui existente, o método `carregar_diario_salvo()` lê os comandos persistidos em `diario_salvo.bin` e os empilha no `QUndoStack` com a flag silenciosa (`armar_carregamento_silencioso()`).

Embora o método `cmd.redo()` seja suprimido para evitar mutações desnecessárias no modelo consolidado, o `QUndoStack` do Qt emite o sinal `indexChanged` para cada comando empilhado. O método `GerenciadorHistorico._on_index_changed` recebe o evento e invoca `_despachar_sinal(cmd)`, que por sua vez avalia `id(cmd.msg)` para despachar sinais reativos de interface (`sinal_campo_alterado`, `sinal_item_adicionado`, etc.).

Como comandos antigos podem referenciar entidades que foram removidas ou reordenadas antes do salvamento, a resolução tardia (`navegar_para_mensagem`) em `_obter_msg()` falha, emitindo rajadas de `logger.error` no Sentry. Além disso, `_obter_msg()` não possui uma exceção customizada para identificar falhas de busca e possui uma verificação morta de `self._msg_cache` posicionada após o bloco que retorna `None`.

## Goals / Non-Goals

**Goals:**
- Silenciar o despacho de sinais no `GerenciadorHistorico` durante o carregamento de diários (`carregar_diario_salvo` e `restaurar_do_diario`), evitando disparar eventos de interface e acessos ansiosos a `cmd.msg` durante o boot.
- Introduzir a exceção customizada `MensagemAlvoNaoEncontradaError(LookupError)` para tipar falhas na resolução tardia de entidades Protobuf.
- Blindar `_despachar_sinal` para descartar com segurança qualquer comando cuja mensagem alvo resulte em `None` ou dispare `MensagemAlvoNaoEncontradaError`, evitando a emissão de sinais com `id(None)`.
- Corrigir a ordem de validação em `_obter_msg()` para aproveitar `_msg_cache` quando válido e retornar `None` com log contextual adequado apenas durante operações ativas.

**Non-Goals:**
- Alterar o formato binário ou a lógica de serialização de `diario_salvo.bin` e `diario_pendente.bin`.
- Modificar os sinais públicos emitidos por `CroquiModel` para as Views.

## Decisions

### Decisão 1: Silenciamento de `_on_index_changed` durante `_gravacao_pausada`
- **Abordagem adotada**: Em `GerenciadorHistorico._on_index_changed`, verificar `if self._gravacao_pausada: return`.
  - Como `carregar_diario_salvo` já ativa `self._gravacao_pausada = True` durante todo o loop de carga e a desativa no bloco `finally`, essa checagem elimina por completo o processamento de sinais e o acesso ansioso a `cmd.msg` no boot.
  - Nenhum componente de interface precisa ou deve receber sinais incrementais enquanto o croqui ainda está montando sua pilha inicial.
- **Alternativas consideradas**:
  - *Desconectar temporariamente o sinal `indexChanged`*: Exige gerenciar conexões dinâmicas do Qt com risco de desconexão duplicada ou vazamento se uma exceção ocorrer no meio do loop. A flag booleana `_gravacao_pausada` já encapsula exatamente o estado em que o histórico não deve produzir efeitos colaterais externos.

### Decisão 2: Exceção customizada `MensagemAlvoNaoEncontradaError(LookupError)`
- **Abordagem adotada**: Criar `MensagemAlvoNaoEncontradaError` herdando de `LookupError` em `editor/commands/comandos_protobuf.py`.
  - O `carregar_diario_salvo` e `restaurar_do_diario` já possuem cláusula `except (ValueError, AttributeError, LookupError, TypeError) as e:`.
  - Herdar de `LookupError` garante que, caso qualquer método de recuperação ou inspeção capture exceções de busca, o comando inválido seja tratado nativamente como aviso de descarte sem gerar crashes inesperados ou quebrar o fluxo de inicialização.
- **Alternativas consideradas**:
  - *Usar apenas `KeyError` ou `IndexError` nativos*: São exceções genéricas demais do Python e não comunicam explicitamente que a falha ocorreu na navegação estrutural de uma árvore Protobuf pelo caminho `caminho_msg`.

### Decisão 3: Defesa em `_despachar_sinal` contra alvos nulos
- **Abordagem adotada**: Em `_despachar_sinal`, encapsular a obtenção de `cmd.msg` protegendo contra `None` ou `MensagemAlvoNaoEncontradaError`.
  - Se `target_msg is None`, a função simplesmente retorna sem emitir o sinal.
  - Isso garante que, mesmo fora do boot (por exemplo, se um comando na pilha de Undo referenciar uma entidade que foi limpa em cascata), a UI nunca receberá eventos com `id(None)`.
- **Alternativas consideradas**:
  - *Lançar exceção*: Quebraria o despachante de eventos da pilha de Undo, interrompendo ações do usuário no meio da interface.

### Decisão 4: Ordem de resolução em `ComandoEditor._obter_msg()`
- **Abordagem adotada**: Em `_obter_msg()`, se `self._msg_cache is not None`, verificar se ele ainda pertence ao modelo ou utilizá-lo com segurança se a navegação pelo caminho estiver indisponível.
  - Para inspeções passivas, registrar aviso em nível de debug ou warning controlado, evitando reportar como erro crítico do Sentry comandos inativos que apenas residem na pilha.

## Risks / Trade-offs

- **[Risco] Omissão de atualização de UI se `_gravacao_pausada` for mantida indevidamente**:
  - *Mitigação*: `_gravacao_pausada` é estritamente garantida por blocos `try ... finally` em `carregar_diario_salvo` e `restaurar_do_diario`.
- **[Risco] Quebra de testes de histórico que dependiam de sinais durante a carga**:
  - *Mitigação*: Os testes unitários existentes validam o carregamento silencioso verificando que `redo()` não é executado; testar explicitamente que sinais de UI não são disparados durante a carga consolida a intenção do "carregamento silencioso".
