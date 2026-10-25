# Spec Delta

## ADDED Requirements

### Requirement: Geração Automática e Determinística de UIDs em Comandos de Adição e Substituição
Os comandos canônicos que introduzem ou substituem mensagens Protobuf na árvore do croqui (`CmdAdicionarRepeated` e `CmdAlterarCampo` nas modalidades de item de lista, `oneof` e submensagem) SHALL garantir automaticamente, no momento de sua instanciação, que toda mensagem ou submensagem com campo `uid` vazio na subárvore recebida receba um NanoID de 14 caracteres antes do congelamento do estado, preservando identificadores pré-existentes em `Undo`, `Redo` e deserialização.

#### Scenario: Adição de entidade sem UID em lista repeated gera NanoID imediatamente
- **WHEN** `CmdAdicionarRepeated` é instanciado e executado com uma mensagem `Escalada`, `Botao`, `PontoDeInteresse`, `SetorOuGrupo` ou `ArquivoSetor` cujo campo `uid` (direto ou em `.conteudo`) está vazio
- **THEN** o comando atribui imediatamente um `uid` NanoID de 14 caracteres à mensagem (e a quaisquer submensagens com `uid` vazio em sua subárvore), congela esse `uid` em `self.valor` e insere a entidade no `CroquiModel`, tornando-a instantaneamente indexada no `IndiceUidsModel`

#### Scenario: Preservação do mesmo UID após ciclos de Undo e Redo
- **WHEN** uma entidade recém-adicionada via `CmdAdicionarRepeated` recebe um `uid` automático, a ação é desfeita (`undo`) e em seguida refeita (`redo`)
- **THEN** a entidade reinserida no `CroquiModel` preserva exatamente o mesmo `uid` gerado na instanciação inicial do comando, mantendo válidas quaisquer referências que apontem para ela

#### Scenario: Preservação de UID pré-existente na instanciação e deserialização
- **WHEN** `CmdAdicionarRepeated` ou `CmdAlterarCampo` é instanciado ou deserializado do diário com uma mensagem que já possui o campo `uid` preenchido
- **THEN** o comando preserva inalterado o `uid` original sem sobrescrevê-lo

#### Scenario: Alteração de variante oneof ou submensagem gera UID quando vazio
- **WHEN** `CmdAlterarCampo` é instanciado para definir ou substituir uma variante de `oneof`, submensagem singular ou item de lista `repeated` cuja nova mensagem possui campo `uid` vazio
- **THEN** o comando preenche automaticamente o `uid` na nova mensagem antes de congelar `valor_novo` e aplica a mutação indexando o novo `uid` no `IndiceUidsModel`
