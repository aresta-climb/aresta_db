# Spec Delta: editor-diario-recuperacao

## MODIFIED Requirements

### Requirement: Tolerância a Falhas na Leitura do Diário
O parser de leitura do diário e o carregador do histórico de comandos salvos SHALL ser resiliente a encerramentos abruptos durante a escrita de um registro e a inconsistências estruturais na deserialização de comandos de sessões passadas. O carregador SHALL capturar e ignorar com segurança exceções de busca e índice (`LookupError`, incluindo `MensagemAlvoNaoEncontradaError`, `IndexError` e `KeyError`), bem como `ValueError`, `AttributeError` e `TypeError`, descartando o comando inconsistente com log de aviso e processando todos os demais comandos íntegros até o final do diário. Além disso, durante a reconstrução do diário na pilha de desfazer, o despacho de eventos reativos de interface SHALL permanecer silenciado para prevenir acessos ansiosos a mensagens inexistentes.

#### Scenario: Leitura de diário com registro incompleto no fim do arquivo
- **WHEN** o editor lê um `diario_pendente.bin` cujo último comando foi cortado por falta de energia
- **THEN** os comandos íntegros anteriores são restaurados com sucesso e o erro de final de arquivo é tratado sem abortar a inicialização.

#### Scenario: Leitura de diário salvo com comando referenciando índice ausente
- **WHEN** o editor lê um comando em `diario_salvo.bin` cuja deserialização ou validação falha com `IndexError`, `MensagemAlvoNaoEncontradaError` ou `LookupError`
- **THEN** o comando inválido é descartado com log de aviso e a inicialização do editor prossegue normalmente carregando os demais comandos válidos sem disparar erro não tratado para telemetria

#### Scenario: Silenciamento de sinais reativos durante carregamento silencioso do diário
- **WHEN** `carregar_diario_salvo` empilha múltiplos comandos na `QUndoStack` com carregamento silencioso armado
- **THEN** o gerenciador de histórico suprime a execução de `_despachar_sinal`, impedindo a resolução ansiosa de propriedades de entidade e a emissão de sinais de UI para instâncias nulas ou desatualizadas
