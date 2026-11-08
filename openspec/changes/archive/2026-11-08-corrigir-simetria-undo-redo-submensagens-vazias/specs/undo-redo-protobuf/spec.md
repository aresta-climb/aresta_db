# Spec Delta

## MODIFIED Requirements

### Requirement: Comandos de Edição Protobuf Genericos
O sistema SHALL encapsular e restringir a criação e execução de comandos granulares (`QUndoCommand`) estritamente à camada de `commands/` coordenados pelos `controllers/` e ferramentas MCP. A interface do usuário (View) na aba de Dados NÃO PODE criar e empilhar comandos diretamente ou mutar propriedades. Todas as alterações de campos singulares (escalares primitivos, renomeações de entidades, submensagens singulares, seleção/limpeza de `oneof` e substituição de item por índice em lista `repeated`) SHALL ser realizadas pelo comando canônico unificado `CmdAlterarCampo` em `editor/commands/comandos_protobuf.py`, guiado por introspecção do `DESCRIPTOR` Protobuf (Reflection). Todos os comandos canônicos derivados de `ComandoEditor` SHALL definir um rótulo textual descritivo não vazio (`QUndoCommand.text()`) no momento de sua instanciação. Quando uma mutação aplicada por `CmdAlterarCampo` (seja em `executar_redo()` ou `undo()`) limpar o último campo preenchido de uma submensagem singular opcional que não pertença a um `oneof` (deixando `ListFields()` vazio), o sistema SHALL limpar em cascata a presença da submensagem vazia na mensagem ancestral (`ClearField`), preservando a simetria determinística binária entre `Undo` e `Redo`.

#### Scenario: Edição Primitiva em Protobuf
- **WHEN** o usuário digita em um campo gerado para um tipo String ou escalar do Protobuf (incluindo o campo `nome` de uma escalada) na View
- **THEN** a View envia a intenção ao Controller apropriado, que cria e empilha um comando `CmdAlterarCampo` (da pasta `commands/`) resolvendo automaticamente o tipo pelo `DESCRIPTOR` e capturando o valor anterior do modelo. Sucessivas digitações ininterruptas no mesmo alvo, campo e `session_id` SHALL invocar o merge (`mergeWith`) do comando para evitar inflar o histórico de desfazer letra por letra.

#### Scenario: Alteração de variante oneof ou submensagem singular via CmdAlterarCampo
- **WHEN** o usuário seleciona outra variante de um `oneof` (ex.: `tipo_escalada` ou `alvo_referencia`), limpa um `oneof` (`valor_novo=None`) ou substitui uma submensagem singular (ex.: `metadados` em `CaminhoNovo`)
- **THEN** `CmdAlterarCampo` detecta via `DESCRIPTOR` se o identificador corresponde a um `oneof` ou `MESSAGE` singular, captura o estado anterior completo (incluindo a variante ativa anterior do `oneof` ou cópia da submensagem) e restaura esse estado exato ao acionar Desfazer (Undo)

#### Scenario: Alteração de item específico de lista repeated por índice via CmdAlterarCampo
- **WHEN** `CmdAlterarCampo` recebe um `campo_nome` indexado no formato `"<campo>.<indice>"` (ex.: `"graduacoes.0"` ou `"conquistadores.1"`)
- **THEN** o comando identifica via `DESCRIPTOR` o campo `repeated`, captura o elemento na posição `<indice>` como `valor_antigo` e substitui apenas aquela posição no `executar_redo()` e no `undo()`

#### Scenario: Simetria de Undo e Redo ao editar campo de submensagem singular inicialmente ausente
- **WHEN** o usuário ou ferramenta edita um campo escalar dentro de uma submensagem singular opcional que ainda não estava presente no objeto pai (ex.: `latitude` em `Setor.localizacao_estacionamento` onde `setor.HasField("localizacao_estacionamento") == False`) e em seguida aciona Desfazer (Undo)
- **THEN** o comando limpa o campo escalar e remove a presença da submensagem vazia no objeto pai (`setor.HasField("localizacao_estacionamento") == False`), restaurando exatamente o mesmo hash de serialização binária determinística anterior à edição, e ao acionar Refazer (Redo) reaplica o valor reativando a submensagem no pai

#### Scenario: Rótulo descritivo não vazio nos comandos canônicos da pilha de histórico
- **WHEN** qualquer comando canônico (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo` ou `CmdMacro`) é instanciado e empilhado na `QUndoStack`
- **THEN** `comando.text()` SHALL retornar uma descrição textual não vazia identificando a operação e o campo/alvo afetado

### Requirement: Resolução Tardia de Mensagens Alvo em Comandos Protobuf
Os comandos derivados de `ComandoEditor` que operam sobre mensagens da árvore Protobuf SHALL armazenar e utilizar resolução tardia (*lazy resolution*) através de um identificador de `alvo` em três níveis:
1. **`UID` direto** (ex.: `"esc_1234"`): quando a mensagem possui campo `uid` registrado no `IndiceUidsModel` (ou é a variante ativa de uma `Escalada` com `uid`).
2. **Ancoragem no ancestral mais próximo com `UID` + subcaminho relativo** (ex.: `"setor_abcd.imagens.0"` ou `"esc_1234.via.0.caminho"`): quando a submensagem não possui `uid` próprio, mas descende de uma entidade com `uid`.
3. **Fallback posicional global desde a raiz** (ex.: `"picos.0.imagens.1"` ou `"mapas.0.referencias.2"`): quando nenhum ancestral possui `uid`.

A mensagem alvo viva no modelo SHALL ser resolvida dinamicamente a partir da árvore ativa via `caminho_msg` no momento da execução das operações de `undo()` e `executar_redo()`, atualizando o cache interno para a instância viva atual e recorrendo a `_msg_cache` apenas como fallback caso a navegação não localize o caminho. Componentes visuais de formulário que editam submensagens singulares inline (como `WidgetMensagemCoordenada`) SHALL manter ou re-resolver a referência da submensagem a partir do objeto pai ativo sempre que a submensagem for limpa e recriada por `ClearField`. Caso a mensagem alvo não exista, esteja fora dos limites de repetição ou inacessível, o sistema SHALL tratar a falha através da exceção tipada `MensagemAlvoNaoEncontradaError(LookupError)` ou retorno `None` seguro, abortando a operação sem corromper a árvore.

#### Scenario: Execução de undo com mensagem alvo existente via caminho
- **WHEN** o usuário aciona Desfazer (Undo) em um comando deserializado ou executado previamente cujo `alvo` (`caminho_msg`) é um `UID` (`"esc_1234"`), um subcaminho ancorado em `UID` (`"esc_1234.via.0"`) ou um caminho posicional desde a raiz (`"picos.0"`)
- **THEN** o comando consulta o `IndiceUidsModel` em $O(1)$ (quando ancorado em `UID`) ou navega a partir da raiz `Croqui` pelo `caminho_msg`, localiza a instância viva correspondente e aplica a reversão com sucesso

#### Scenario: Re-resolução de submensagem viva após limpeza no objeto pai
- **WHEN** uma submensagem singular opcional (ex.: `localizacao_estacionamento`) é limpa no pai via `ClearField` durante um `Undo` e em seguida o usuário executa `Redo` ou edita novamente os campos da submensagem no formulário em cache
- **THEN** tanto o comando na `QUndoStack` quanto o widget no formulário resolvem e operam sobre a nova instância viva da submensagem anexada ao pai, sem mutar referências órfãs desanexadas e sem lançar `ValueError`

#### Scenario: Execução de undo com mensagem alvo inexistente ou índice fora de limite
- **WHEN** o usuário aciona Desfazer (Undo) e a mensagem alvo não pode ser resolvida pelo `alvo` (por exemplo, `UID` inexistente, nó excluído ou índice fora dos limites)
- **THEN** o comando SHALL registrar uma mensagem de erro explícita em log reportando a falha de reversão do alvo e não aplicar mutações inconsistentes no modelo

#### Scenario: Navegação segura com tratamento de limites e oneofs inativos
- **WHEN** o sistema navega pela árvore do modelo através de um caminho contendo índices de lista ou seleções de `oneof`
- **THEN** o navegador SHALL verificar os limites de repetição da lista antes de indexar e verificar se a variante do `oneof` está ativa, retornando `None` de forma segura caso o caminho seja inválido em vez de disparar exceções não tratadas

#### Scenario: Despacho de sinal ignora comando com mensagem alvo nula ou não resolvida
- **WHEN** o sistema processa um comando cuja mensagem alvo não pôde ser resolvida no modelo
- **THEN** nenhuma emissão de sinais reativos inconsistentes com identificador nulo SHALL ocorrer
