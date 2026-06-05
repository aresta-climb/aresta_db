## MODIFIED Requirements

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
