# undo-redo-global Specification

## Purpose
TBD - created by archiving change add-undo-redo. Update Purpose after archive.
## Requirements
### Requirement: Gerenciamento Global de Undo/Redo
O sistema SHALL prover uma pilha global unificada de Desfazer/Refazer acessível a partir da Janela Principal (via botões de toolbar e atalhos Ctrl+Z / Ctrl+Shift+Z), que controle as mutações de dados independentemente da aba ativa.

#### Scenario: Sincronização entre abas
- **WHEN** o usuário faz uma edição na aba de Dados e em seguida move uma imagem na aba de Imagens, e então aciona Desfazer duas vezes
- **THEN** a primeira ação desfaz o movimento da imagem e a segunda desfaz a edição de dados, respeitando estritamente a cronologia global.

### Requirement: Integração com Foco de UI
O sistema SHALL tentar restaurar o foco e a seleção de texto ao máximo quando uma operação de Undo/Redo acarretar no redesenho parcial ou total de um formulário da interface.

#### Scenario: Undo durante digitação
- **WHEN** o usuário clica fora de um campo de texto após alterá-lo e aciona Desfazer
- **THEN** o valor antigo do campo de texto é restaurado e o formulário é atualizado.

### Requirement: Exclusão Segura de Arquivos Físicos
Arquivos do projeto (Imagens, Markdown, JSON, etc) SHALL NOT ser excluídos em definitivo (`os.remove`) do sistema de arquivos durante a operação do editor, para que a ação de Undo estrutural possa restaurar o arquivo físico.

#### Scenario: Excluir arquivo e desfazer
- **WHEN** o usuário realiza uma operação que deleta um arquivo do projeto via interface
- **THEN** o arquivo físico correspondente é movido para um diretório temporário interno (`.trash_interna`).
- **WHEN** o usuário aciona Desfazer
- **THEN** o arquivo é restaurado do diretório da lixeira de volta ao seu caminho original no projeto.

### Requirement: Serialização e Deserialização de Comandos de Histórico
Todos os comandos `QUndoCommand` utilizados no Editor Aresta SHALL implementar os métodos de serialização `serializar(anonimizado: bool = False) -> dict` e deserialização `deserializar(dados: dict, model: CroquiModel) -> QUndoCommand`, permitindo a conversão bidirecional entre a instância em memória e sua representação pura em dicionário serializável.

#### Scenario: Serialização padrão com dados completos
- **WHEN** o método `serializar(anonimizado=False)` é chamado em um comando que contém imagem (ex: `CmdSubstituirImagemMemoria`)
- **THEN** o dicionário resultante contém os bytes originais da imagem para persistência local no diário.

#### Scenario: Serialização anonimizada para telemetria
- **WHEN** o método `serializar(anonimizado=True)` é chamado em um comando que contém imagem
- **THEN** os bytes da imagem são substituídos pelo WebP anonimizado homogêneo de dimensões equivalentes, protegendo a privacidade e reduzindo o payload.

#### Scenario: Deserialização e reconstrução de comando
- **WHEN** o método `deserializar(dados, model)` é invocado a partir de um registro de diário
- **THEN** uma nova instância do respectivo `QUndoCommand` é instanciada e configurada com os parâmetros do dicionário e a referência do modelo alvo.

