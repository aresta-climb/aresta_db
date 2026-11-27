# Spec Delta

## ADDED Requirements

### Requirement: Invalidação de Diários após Execução de Migrações
Sempre que o motor de migrações executar ao menos uma migração pendente nos arquivos de um croqui durante sua abertura, o sistema SHALL invalidar e limpar integralmente tanto o histórico consolidado (`diario_salvo.bin`) quanto o histórico pendente (`diario_pendente.bin`) e os respectivos caches em memória antes de inicializar a pilha de desfazer/refazer da sessão.

#### Scenario: Limpeza automática de diários quando migração altera o croqui na abertura
- **WHEN** o usuário abre um croqui experimental que possui `diario_salvo.bin` ou `diario_pendente.bin` de sessões anteriores e `aplicar_migracoes` executa uma ou mais migrações pendentes
- **THEN** ambos os arquivos de diário são limpos/truncados antes do carregamento do histórico, nenhum diálogo de recuperação obsoleto é exibido e a pilha `QUndoStack` inicia limpa e sincronizada com o novo estado migrado

#### Scenario: Preservação de diários quando nenhuma migração é executada
- **WHEN** o usuário abre um croqui experimental já atualizado (`aplicar_migracoes` retorna `False`)
- **THEN** `diario_salvo.bin` e `diario_pendente.bin` são preservados e processados normalmente na abertura

## MODIFIED Requirements

### Requirement: Tolerância a Falhas na Leitura do Diário
O parser de leitura do diário e o carregador do histórico de comandos salvos SHALL ser resiliente a encerramentos abruptos durante a escrita de um registro e a inconsistências estruturais na deserialização de comandos de sessões passadas. O carregador SHALL capturar e ignorar com segurança exceções de busca e índice (`LookupError`, incluindo `MensagemAlvoNaoEncontradaError`, `IndexError` e `KeyError`), bem como `ValueError`, `AttributeError` e `TypeError`, descartando o comando inconsistente com log de aviso e processando todos os demais comandos íntegros até o final do diário. Durante a reconstrução do diário na pilha de desfazer, tanto a deserialização dos comandos quanto o empilhamento com carregamento silencioso SHALL operar sem consultar a árvore atual do modelo e com o despacho de eventos reativos de interface silenciado, garantindo zero emissões de log de erro para passos históricos intermediários.

#### Scenario: Leitura de diário com registro incompleto no fim do arquivo
- **WHEN** o editor lê um `diario_pendente.bin` cujo último comando foi cortado por falta de energia
- **THEN** os comandos íntegros anteriores são restaurados com sucesso e o erro de final de arquivo é tratado sem abortar a inicialização.

#### Scenario: Leitura de diário salvo com comando referenciando índice ausente
- **WHEN** o editor lê um comando em `diario_salvo.bin` cuja deserialização falha com `IndexError`, `MensagemAlvoNaoEncontradaError` ou `LookupError`
- **THEN** o comando inválido é descartado com log de aviso e a inicialização do editor prossegue normalmente carregando os demais comandos válidos sem disparar erro não tratado para telemetria

#### Scenario: Carregamento silencioso de passos intermediários sem erros falsos-positivos
- **WHEN** `carregar_diario_salvo` lê comandos válidos de passos intermediários cujos alvos foram posteriormente movidos para grupos, excluídos ou tiveram sua variante `oneof` alterada antes do salvamento final
- **THEN** todos os comandos são empilhados silenciosamente na `QUndoStack` sem emitir nenhum log de nível `ERROR` e permanecem prontos para reversão ordenada via Desfazer (Undo)

#### Scenario: Silenciamento de sinais reativos durante carregamento silencioso do diário
- **WHEN** `carregar_diario_salvo` empilha múltiplos comandos na `QUndoStack` com carregamento silencioso armado
- **THEN** o gerenciador de histórico suprime a execução de `_despachar_sinal`, impedindo a resolução ansiosa de propriedades de entidade e a emissão de sinais de UI para instâncias nulas ou desatualizadas
