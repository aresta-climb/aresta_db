## ADDED Requirements

### Requirement: Comandos de Edição Protobuf Genericos
O sistema DEVE converter toda edição na aba de Dados em comandos granulares (`QUndoCommand`) operando na árvore Protobuf, em vez de mutar propriedades diretamente nos callbacks de UI.

#### Scenario: Edição Primitiva em Protobuf
- **WHEN** o usuário digita em um campo gerado para um tipo String do Protobuf
- **THEN** um comando `CmdAlterarPrimitivo` é criado e empilhado. Sucessivas digitações ininterruptas no mesmo campo DEVEM invocar o merge do comando para evitar inflar o histórico de desfazer letra por letra.

### Requirement: Proteção contra Exclusão Estrutural
O sistema DEVE suportar a reversão de comandos destrutivos que alteram a hierarquia da árvore, como remoções de itens repetidos ou mudança do campo ativo em um `oneof`.

#### Scenario: Remoção de item em lista repeated
- **WHEN** o usuário clica no botão "Remover" de uma sub-mensagem gerada dinamicamente
- **THEN** um comando é gerado e retém em memória uma cópia profunda (`CopyFrom`) da mensagem excluída.
- **WHEN** o usuário aciona Desfazer
- **THEN** o comando reinsere a mensagem no exato índice de onde foi removida e notifica a árvore.
