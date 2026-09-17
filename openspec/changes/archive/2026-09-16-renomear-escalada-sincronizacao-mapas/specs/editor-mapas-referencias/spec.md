## ADDED Requirements

### Requirement: Sincronização Automática ao Renomear Escaladas
O sistema SHALL sincronizar automaticamente todas as referências em mapas (`croqui_pb2.Mapa.Referencia`) associadas a uma escalada quando o seu nome for alterado através do formulário de dados da interface gráfica (`WidgetEditorDados`), preservando a integridade referencial do croqui sem requerer intervenção manual do usuário.

#### Scenario: Edição transparente do nome da via
- **WHEN** o usuário altera o campo `nome` de uma escalada no formulário de dados
- **THEN** o controlador SHALL localizar todas as referências em mapas do pico que apontam para essa escalada
- **THEN** o controlador SHALL aplicar `CmdRenomearEscalada` para atualizar o nome da escalada e de todas as referências localizadas
- **THEN** os sinais `dado_alterado` do modelo SHALL ser emitidos para a escalada e para cada referência modificada, atualizando instantaneamente as visões de mapa abertas

### Requirement: Resolução Simétrica de Escopo Implícito e Explícito de Referências
O sistema SHALL fornecer uma biblioteca autônoma `referencias_util.py` para determinar se uma referência de mapa aponta para uma escalada específica, considerando de forma simétrica tanto o setor efetivo quanto o grupo efetivo.

#### Scenario: Referência com setor implícito no mesmo setor
- **WHEN** o mapa pertencer ao setor `Setor 1` e a referência tiver `ref.escalada == "Via Base"` com `ref.setor == ""`
- **THEN** o setor efetivo SHALL ser resolvido como `Setor 1` e a referência SHALL ser vinculada à escalada `"Via Base"` do `Setor 1`

#### Scenario: Referência com setor explícito em mapa vizinho ou mapa geral
- **WHEN** um mapa pertencer a `Setor 2` (ou ao pico/grupo) e possuir referência com `ref.escalada == "Via Base"` e `ref.setor == "Setor 1"`
- **THEN** o setor efetivo SHALL ser resolvido como `Setor 1` e a referência SHALL ser vinculada à escalada `"Via Base"` do `Setor 1`

#### Scenario: Referência com grupo implícito no mapa de grupo
- **WHEN** o mapa pertencer ao `Grupo A` e possuir referência para um setor do grupo com `ref.grupo == ""`
- **THEN** o grupo efetivo SHALL ser resolvido como `Grupo A` e casar estritamente com escaladas pertencentes ao `Grupo A`

### Requirement: Isolamento de Mesclagem por Sessão de Foco na Edição de Nome
O sistema SHALL delimitar a mesclagem contínua (`mergeWith`) de comandos de renomeação estritamente ao ciclo de vida de foco do campo de entrada (`focusInEvent` a `focusOutEvent`).

#### Scenario: Nova busca de referências ao refocar o campo
- **WHEN** o usuário conclui uma edição, o campo perde o foco e posteriormente uma nova referência de mapa é criada para aquela escalada
- **WHEN** o usuário foca novamente no campo de nome e inicia uma nova alteração
- **THEN** uma nova sessão de edição SHALL ser iniciada
- **THEN** o comando SHALL NÃO mesclar com a sessão anterior
- **THEN** uma nova busca completa SHALL ser executada, descobrindo tanto as referências antigas quanto a nova referência criada
