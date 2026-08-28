## ADDED Requirements

### Requirement: Gravação Transacional de Comandos em Modo Append-Only
O sistema SHALL persistir cada comando executado na pilha de histórico (`QUndoStack`) no arquivo binário `diario_pendente.bin` localizado na pasta do croqui experimental, utilizando a biblioteca `editor/core/diario.py` e serialização `pickle` em modo append (`"ab"`), com tempo de escrita de baixa latência e desacoplado de mutações no sistema de arquivos do croqui.

#### Scenario: Execução de comando e persistência imediata
- **WHEN** um `QUndoCommand` é empilhado e executado na `QUndoStack`
- **THEN** os dados serializados do comando (`serializar(anonimizado=False)`) são anexados instantaneamente ao arquivo `diario_pendente.bin`.

### Requirement: Consolidação de Histórico no Salvamento
Ao executar o salvamento e compilação do croqui experimental, o sistema SHALL transferir (fazer append) de todos os comandos contidos em `diario_pendente.bin` para o arquivo `diario_salvo.bin`, e em seguida truncar `diario_pendente.bin` para 0 bytes.

#### Scenario: Salvamento com sucesso
- **WHEN** o usuário aciona o salvamento do croqui e o commit local é finalizado com sucesso
- **THEN** os comandos pendentes são consolidados em `diario_salvo.bin` e `diario_pendente.bin` fica vazio.

### Requirement: Detecção de Encerramento Anômalo e Recuperação de Sessão
Ao carregar um croqui experimental, o sistema SHALL inspecionar o arquivo `diario_pendente.bin`. Se o arquivo possuir tamanho maior que zero, o sistema SHALL exibir o diálogo modal `editor/views/dialogo_recuperacao_sessao.py` informando ao usuário sobre alterações não salvas detectadas da sessão anterior, oferecendo as opções "Recuperar Trabalho" e "Descartar".

#### Scenario: Usuário escolhe recuperar trabalho não salvo
- **WHEN** o usuário seleciona a opção "Recuperar Trabalho" no diálogo de recuperação
- **THEN** o editor carrega os dados consolidados do croqui e executa o replay ordenado de todos os comandos deserializados de `diario_pendente.bin`, populando a `QUndoStack` para que o usuário possa continuar trabalhando ou acionar Desfazer (Undo).

#### Scenario: Usuário escolhe descartar trabalho não salvo
- **WHEN** o usuário seleciona a opção "Descartar" no diálogo de recuperação
- **THEN** o arquivo `diario_pendente.bin` é truncado/deletado e o croqui é aberto em seu estado salvo anterior.

### Requirement: Tolerância a Falhas na Leitura do Diário
O parser de leitura do diário SHALL ser resiliente a encerramentos abruptos durante a escrita de um registro, processando todos os comandos gravados com sucesso até o ponto de corrupção e descartando registros parciais de final de arquivo.

#### Scenario: Leitura de diário com registro incompleto no fim do arquivo
- **WHEN** o editor lê um `diario_pendente.bin` cujo último comando foi cortado por falta de energia
- **THEN** os comandos íntegros anteriores são restaurados com sucesso e o erro de final de arquivo é tratado sem abortar a inicialização.
