## MODIFIED Requirements

### Requirement: Tolerância a Falhas na Leitura do Diário
O parser de leitura do diário e o carregador do histórico de comandos salvos SHALL ser resiliente a encerramentos abruptos durante a escrita de um registro e a inconsistências estruturais na deserialização de comandos de sessões passadas. O carregador SHALL capturar e ignorar com segurança exceções de busca e índice (`LookupError`, cobrindo `IndexError` e `KeyError`), bem como `ValueError`, `AttributeError` e `TypeError`, descartando o comando inconsistente com log de aviso e processando todos os demais comandos íntegros até o final do diário.

#### Scenario: Leitura de diário com registro incompleto no fim do arquivo
- **WHEN** o editor lê um `diario_pendente.bin` cujo último comando foi cortado por falta de energia
- **THEN** os comandos íntegros anteriores são restaurados com sucesso e o erro de final de arquivo é tratado sem abortar a inicialização.

#### Scenario: Leitura de diário salvo com comando referenciando índice ausente
- **WHEN** o editor lê um comando em `diario_salvo.bin` cuja deserialização ou validação falha com `IndexError` ou `LookupError`
- **THEN** o comando inválido é descartado com log de aviso e a inicialização do editor prossegue normalmente carregando os demais comandos válidos sem disparar erro não tratado para telemetria
