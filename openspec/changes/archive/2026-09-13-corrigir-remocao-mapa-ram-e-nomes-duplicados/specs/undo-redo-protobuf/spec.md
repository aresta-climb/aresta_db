## MODIFIED Requirements

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
