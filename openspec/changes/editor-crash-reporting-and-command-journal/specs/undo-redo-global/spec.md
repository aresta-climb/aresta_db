## ADDED Requirements

### Requirement: Serialização e Deserialização de Comandos de Histórico
Todos os comandos `QUndoCommand` utilizados no Editor Aresta SHALL implementar os métodos de serialização `serializar(redacted: bool = False) -> dict` e deserialização `deserializar(dados: dict, model: CroquiModel) -> QUndoCommand`, permitindo a conversão bidirecional entre a instância em memória e sua representação pura em dicionário/binário.

#### Scenario: Serialização padrão com dados completos
- **WHEN** o método `serializar(redacted=False)` é chamado em um comando que contém imagem (ex: `CmdSubstituirImagemMemoria`)
- **THEN** o dicionário resultante contém os bytes originais da imagem para persistência local no journal.

#### Scenario: Serialização redigida para telemetria
- **WHEN** o método `serializar(redacted=True)` é chamado em um comando que contém imagem
- **THEN** os bytes da imagem são substituídos pelo dummy WebP homogêneo de dimensões equivalentes, protegendo a privacidade e reduzindo o payload.

#### Scenario: Deserialização e reconstrução de comando
- **WHEN** o método `deserializar(dados, model)` é invocado a partir de um registro de journal
- **THEN** uma nova instância do respectivo `QUndoCommand` é instanciada e configurada com os parâmetros do dicionário e a referência do modelo alvo.
