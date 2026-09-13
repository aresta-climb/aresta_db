# undo-redo-protobuf Specification

## Purpose
TBD - created by archiving change add-undo-redo. Update Purpose after archive.
## Requirements
### Requirement: Comandos de Edição Protobuf Genericos
O sistema DEVE encapsular e restringir a criação e execução de comandos granulares (`QUndoCommand`) estritamente à camada de `commands/` coordenados pelos `controllers/`. A interface do usuário (View) na aba de Dados NÃO PODE criar e empilhar comandos diretamente ou mutar propriedades.

#### Scenario: Edição Primitiva em Protobuf
- **WHEN** o usuário digita em um campo gerado para um tipo String do Protobuf na View
- **THEN** a View envia a intenção ao Controller apropriado, que então cria e empilha um comando `CmdAlterarPrimitivo` (da pasta `commands/`). Sucessivas digitações ininterruptas no mesmo campo DEVEM invocar o merge do comando pelo Controller/Histórico para evitar inflar o histórico de desfazer letra por letra.

### Requirement: Proteção contra Exclusão Estrutural
O sistema DEVE suportar a reversão de comandos destrutivos que alteram a hierarquia da árvore, gerenciada pela camada MVC, de tal forma que a lógica de exclusão permaneça desacoplada da interface.

#### Scenario: Remoção de item em lista repeated
- **WHEN** o usuário clica no botão "Remover" de uma sub-mensagem gerada dinamicamente na View
- **THEN** a View solicita a exclusão ao Controller correspondente
- **THEN** o Controller instancia o comando adequado que retém em memória uma cópia profunda (`CopyFrom`) da mensagem excluída.
- **WHEN** o usuário aciona Desfazer
- **THEN** o comando reinstrui o Model usando os métodos protegidos (`_set_*`) a reinserir a mensagem no exato índice de onde foi removida, fazendo o Model disparar sinais de notificação para a View se atualizar.

#### Scenario: Remoção e restauração de imagens em memória associadas a itens excluídos
- **WHEN** o comando de remoção de item repeated for executado em um item que referencia imagens no buffer de memória RAM
- **THEN** o sistema DEVE identificar se essas imagens não são mais referenciadas em nenhum outro ponto do croqui e removê-las do buffer de memória RAM
- **WHEN** a operação de remoção for desfeita (Desfazer / Undo)
- **THEN** o sistema DEVE restaurar as imagens no buffer de memória RAM e emitir o sinal de alteração de imagem para atualização da interface

### Requirement: Guarda de Integridade Estrutural nos Comandos Protobuf
O sistema SHALL validar a pertinência da mensagem alvo à árvore ativa do croqui na instanciação de qualquer comando Protobuf que opere sobre mensagens filhas (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdAlterarOneof`, `CmdAlterarPrimitivo`, `CmdAlterarCampoImagem`). Se a mensagem alvo não for o nó raiz `Croqui` e o caminho resolvido na árvore ativa for vazio `""`, o comando SHALL lançar imediatamente `ValueError`, impedindo comandos órfãos de entrarem no histórico (`QUndoStack`) ou no diário de persistência. O sistema também SHALL validar que o campo informado pertença aos campos do descriptor da mensagem alvo.

#### Scenario: Tentativa de criação de comando com mensagem desanexada/órfã
- **WHEN** um comando de alteração estrutural ou de campo for instanciado com uma mensagem que não pertence à árvore do `CroquiModel`
- **THEN** o comando SHALL disparar `ValueError` descrevendo que a mensagem alvo é órfã, impedindo a sua execução e gravação no diário

#### Scenario: Criação de comando legítimo na mensagem raiz ou mensagem filha conectada
- **WHEN** um comando for instanciado para alterar um campo da mensagem raiz `Croqui` ou de uma mensagem filha conectada à árvore
- **THEN** o comando SHALL ser criado com sucesso, resolvendo o caminho correto e permitindo execução e serialização normais

#### Scenario: Deserialização de comando com caminho corrompido ou campo inexistente
- **WHEN** o histórico ou diário tentar deserializar um comando cujo caminho seja inválido ou o campo não exista na mensagem resultante
- **THEN** o sistema SHALL registrar o erro em log e descartar o comando com segurança, permitindo que a recuperação de sessão continue sem travar o editor


