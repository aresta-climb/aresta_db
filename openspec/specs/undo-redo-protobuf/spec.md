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

### Requirement: Comandos Compostos Serializáveis (CmdMacro)
O sistema SHALL fornecer a classe `CmdMacro` para agrupar sequências ordenadas de comandos filhos derivados de `ComandoEditor`. O `CmdMacro` SHALL executar os comandos filhos em ordem no `executar_redo()`, em ordem reversa no `undo()`, e propagar `armar_carregamento_silencioso()` para todos os filhos. O `CmdMacro` SHALL implementar métodos `serializar()` e `deserializar()` completos para integração transparente com o `GerenciadorDiario` (`diario_pendente.bin` e `diario_salvo.bin`).

#### Scenario: Execução e reversão de macro
- **WHEN** um `CmdMacro` contendo múltiplos comandos filhos for executado na `QUndoStack`
- **THEN** todos os subcomandos SHALL ser aplicados em ordem no modelo
- **WHEN** o usuário aciona Desfazer (Undo)
- **THEN** todos os subcomandos SHALL ser revertidos em ordem inversa de forma atômica em um único passo da pilha

#### Scenario: Serialização e restauração do diário
- **WHEN** um `CmdMacro` for gravado no `diario_pendente.bin` e posteriormente restaurado via `deserializar_comando`
- **THEN** todos os subcomandos SHALL ser perfeitamente reconstruídos com suas classes e parâmetros originais sem perda de dados

### Requirement: Proibição Arquitetural de Macros Nativos do Qt
O sistema SHALL proibir qualquer chamada direta aos métodos `beginMacro` ou `endMacro` do `QUndoStack` do PySide6 em todo o código-fonte do editor, prevenindo o descarte silencioso de operações pelo diário de persistência. Essa restrição SHALL ser validada de forma automatizada pela suíte de testes de arquitetura.

#### Scenario: Detecção de uso indevido de beginMacro/endMacro
- **WHEN** a suíte de testes de arquitetura (`arquitetura_mvc_test.py`) analisar o código do editor via AST
- **THEN** nenhuma invocação a `beginMacro` ou `endMacro` SHALL ser encontrada
- **WHEN** algum arquivo introduzir chamada a `beginMacro` ou `endMacro`
- **THEN** o teste de arquitetura SHALL falhar imediatamente com mensagem explicativa instruindo o uso de `CmdMacro`

### Requirement: Comando Atômico de Renomeação de Escalada (CmdRenomearEscalada)
O sistema SHALL fornecer `CmdRenomearEscalada` para encapsular a renomeação de uma escalada e a atualização concomitante de todas as referências em mapas (`mapa.referencias`) que apontam para essa escalada no mesmo pico. O comando SHALL suportar mesclagem contínua (`mergeWith`) delimitada pela sessão de foco do usuário.

#### Scenario: Renomeação atômica de escalada e referências
- **WHEN** `CmdRenomearEscalada` for executado para alterar o nome de uma escalada de `Nome A` para `Nome B`
- **THEN** o nome da escalada no modelo SHALL ser alterado para `Nome B`
- **THEN** todas as mensagens `croqui_pb2.Mapa.Referencia` previamente identificadas como vinculadas àquela escalada SHALL ter seu campo `escalada` atualizado para `Nome B`
- **WHEN** o comando for desfeito (Undo)
- **THEN** tanto a escalada quanto todas as referências vinculadas SHALL retornar ao `Nome A` em um único passo



