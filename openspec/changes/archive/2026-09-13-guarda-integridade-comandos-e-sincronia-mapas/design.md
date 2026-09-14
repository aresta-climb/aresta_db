## Context

Atualmente, o editor do Aresta utiliza uma arquitetura baseada em `CroquiModel`, `QUndoStack` e comandos granulares de edição Protobuf (`editor/commands/comandos_protobuf.py`). Toda mutação empilhada é persistida em tempo real em um diário binário (`diario_pendente.bin`).

Conforme documentado em `proposal.md`, identificou-se uma falha silenciosa em que `resolver_caminho_mensagem(root_msg, target_msg)` retorna `""` tanto quando `target_msg` é a própria raiz `Croqui` quanto quando `target_msg` não é encontrada na árvore (objeto órfão desanexado). Quando o `WidgetEditorMapas` reteve uma referência zumbi a um mapa removido/substituído, sucessivos comandos de adição de POIs e linhas foram criados com `caminho_msg: ""` e executados sobre o objeto em memória desconectado, gerando dezenas de comandos corrompidos no diário e falha ao reabrir o editor.

## Goals / Non-Goals

**Goals:**
- Proteger todos os comandos Protobuf que atuam sobre nós/mensagens filhas contra instanciação e execução com mensagens órfãs.
- Lançar `ValueError` imediato e explícito caso `resolver_caminho_mensagem` retorne `""` para mensagens que não sejam o nó raiz `Croqui`.
- Validar a existência do campo informado no `DESCRIPTOR` da mensagem alvo.
- No `WidgetEditorMapas`, sincronizar reativamente as remoções e adições de mapas (`campo_nome == 'mapas'`), atualizando a lista lateral e resetando a cena caso o mapa selecionado seja removido.
- Adicionar checagem de mapa ativo válido no `WidgetEditorMapas` antes de despachar qualquer comando de edição ou adição de POIs/linhas/referências.
- Garantir que a recuperação de sessão no `historico.py` descarte com segurança comandos corrompidos legados sem abortar a carga do croqui.

**Non-Goals:**
- Não alterar a estrutura binária dos arquivos de diário (`diario_pendente.bin`, `diario_salvo.bin`).
- Não modificar as definições do schema Protobuf (`croqui.proto`).
- Não reescrever o motor gráfico do visualizador de mapas além da sincronização e checagem de integridade.

## Decisions

### Decisão 1: Validação Centralizada no Construtor dos Comandos (`__init__`)
- **Abordagem**: Implementar a função auxiliar `validar_mensagem_pertence_ao_croqui(model, msg, campo_nome=None, nome_comando="Comando") -> str` em `comandos_protobuf.py`, invocando-a no `__init__` de todas as classes de comando filhas (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarOneof`, `CmdAlterarPrimitivo`, `CmdAlterarCampoImagem`).
- **Lógica de Verificação**:
  1. Desenvelopar proxies (`ReadOnlyProxy`) de `root` e `msg`.
  2. Se `msg_real is root_real`: o caminho é `""`. Válido somente se `campo_nome` pertencer a `root_real.DESCRIPTOR.fields_by_name`.
  3. Se `msg_real is not root_real`: calcular `caminho = resolver_caminho_mensagem(root_real, msg_real)`. Se `caminho == ""`: lançar `ValueError` com mensagem indicando nó órfão desconectado da árvore ativa.
  4. Se `campo_nome` for fornecido e `msg_real` possuir `DESCRIPTOR`, verificar se `campo_nome in msg_real.DESCRIPTOR.fields_by_name`. Se não estiver, lançar `ValueError`.
- **Alternativas consideradas**:
  - *Validar apenas em `serializar`*: Tarde demais; o comando já teria alterado estado em memória ou entrado na pilha de undo.
  - *Validar apenas na View*: Deixaria outros controllers ou chamadas futuras desprotegidos.

### Decisão 2: Resiliência na Deserialização de Histórico Antigo
- **Abordagem**: No `historico.py` (`restaurar_do_diario` e `carregar_comandos_salvos`) e em `deserializar_comando`, capturar `(ValueError, AttributeError)` decorrentes de comandos órfãos/corrompidos gravados em sessões anteriores, registrando aviso no log e ignorando a entrada corrompida sem abortar o replay dos comandos válidos.
- **Alternativas consideradas**:
  - *Interromper o replay no primeiro erro*: Comportamento atual que fazia o usuário perder comandos válidos subsequentes por causa de um comando corrompido no meio da sessão.

### Decisão 3: Reatividade e Guarda Preventiva no `WidgetEditorMapas`
- **Abordagem**:
  1. Nos métodos reativos `_on_repeated_removido` e `_on_repeated_adicionado`, adicionar tratamento para `campo_nome == 'mapas'`.
  2. Quando um mapa for removido, verificar se `self.msg_mapa_proxy` ainda existe na árvore ativa através de `resolver_caminho_mensagem`. Se foi removido, limpar o visualizador (`self.carregar_mapa(None)`), limpar `self.msg_mapa_proxy = None` e recarregar a lista lateral de mapas.
  3. Adicionar método utilitário `self._mapa_ativo_valido() -> bool` no `WidgetEditorMapas` que confere se `self.msg_mapa_proxy` não é nulo e pertence à árvore ativa do modelo.
  4. Proteger todas as ações de inserção (`adicionar_poi`, `_on_desenho_linha_concluido`, `_on_adicionar_referencia`, etc.) com `self._mapa_ativo_valido()`. Se inválido, emitir log/notificação e abortar a operação.

## Risks / Trade-offs

- **[Risco]** Custo computacional de validar o caminho da mensagem na instanciação do comando.
  → **Mitigação**: A árvore de mensagens do Protobuf tem poucos níveis de profundidade (geralmente <= 4) e dezenas a poucas centenas de nós. O percurso completo de busca em profundidade leva frações de milissegundo (< 0.1ms), imperceptível para a UI.
- **[Risco]** Deserialização de diários legados com comandos gravados com `caminho_msg: ""`.
  → **Mitigação**: A validação no construtor ou deserializador rejeita comandos onde `campo_nome` não pertence à raiz, e `historico.py` trata o descarte seguro da entrada com log descritivo.
