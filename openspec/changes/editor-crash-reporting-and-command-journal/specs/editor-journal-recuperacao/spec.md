## ADDED Requirements

### Requirement: Gravação Transacional de Comandos em Modo Append-Only
O sistema SHALL persistir cada comando executado na pilha de histórico (`QUndoStack`) no arquivo binário `journal_pendente.bin` localizado na pasta do croqui experimental, utilizando `pickle` em modo append (`"ab"`), com tempo de escrita de baixa latência e desacoplado de mutações no sistema de arquivos do croqui.

#### Scenario: Execução de comando e persistência imediata
- **WHEN** um `QUndoCommand` é empilhado e executado na `QUndoStack`
- **THEN** os dados serializados do comando (`serializar(redacted=False)`) são anexados instantaneamente ao arquivo `journal_pendente.bin`.

### Requirement: Consolidação de Histórico no Salvamento
Ao executar o salvamento e compilação do croqui experimental, o sistema SHALL transferir (fazer append) de todos os comandos contidos em `journal_pendente.bin` para o arquivo `journal_salvo.bin`, e em seguida truncar `journal_pendente.bin` para 0 bytes.

#### Scenario: Salvamento com sucesso
- **WHEN** o usuário aciona o salvamento do croqui e o commit local é finalizado com sucesso
- **THEN** os comandos pendentes são consolidados em `journal_salvo.bin` e `journal_pendente.bin` fica vazio.

### Requirement: Detecção de Encerramento Anômalo e Recuperação de Sessão
Ao carregar um croqui experimental, o sistema SHALL inspecionar o arquivo `journal_pendente.bin`. Se o arquivo possuir tamanho maior que zero, o sistema SHALL exibir um diálogo modal informando ao usuário sobre alterações não salvas detectadas da sessão anterior, oferecendo as opções "Recuperar Trabalho" e "Descartar".

#### Scenario: Usuário escolhe recuperar trabalho não salvo
- **WHEN** o usuário seleciona a opção "Recuperar Trabalho" no diálogo de recuperação
- **THEN** o editor carrega os dados consolidados do croqui e executa o replay ordenado de todos os comandos deserializados de `journal_pendente.bin`, populando a `QUndoStack` para que o usuário possa continuar trabalhando ou acionar Desfazer (Undo).

#### Scenario: Usuário escolhe descartar trabalho não salvo
- **WHEN** o usuário seleciona a opção "Descartar" no diálogo de recuperação
- **THEN** o arquivo `journal_pendente.bin` é truncado/deletado e o croqui é aberto em seu estado salvo anterior.

### Requirement: Tolerância a Falhas na Leitura do Journal
O parser de leitura do journal SHALL ser resiliente a encerramentos abruptos durante a escrita de um registro, processando todos os comandos gravados com sucesso até o ponto de corrupção e descartando registros parciais de final de arquivo.

#### Scenario: Leitura de journal com registro incompleto no fim do arquivo
- **WHEN** o editor lê um `journal_pendente.bin` cujo último comando foi cortado por falta de energia
- **THEN** os comandos íntegros anteriores são restaurados com sucesso e o erro de final de arquivo é tratado sem abortar a inicialização.
