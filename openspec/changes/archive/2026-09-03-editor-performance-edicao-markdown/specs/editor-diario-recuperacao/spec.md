## MODIFIED Requirements

### Requirement: Gravação Transacional de Comandos em Modo Append-Only
O sistema SHALL persistir cada comando executado na pilha de histórico (`QUndoStack`) no arquivo binário `diario_pendente.bin` localizado na pasta do croqui experimental, utilizando a biblioteca `editor/core/diario.py` e serialização `pickle` em modo append (`"ab"`), com tempo de escrita de baixa latência e desacoplado de mutações no sistema de arquivos do croqui.
- **Eficiência em Comandos Mesclados**: Quando um comando sofrer coalescência/mesclagem no topo da pilha (`mergeWith`), o sistema SHALL sincronizar a alteração pendente sem descartar o cache de comandos anonimizados em memória e sem disparar releitura completa de arquivos de diário em disco ou reprocessamento síncrono de imagens para o contexto de telemetria a cada tecla.

#### Scenario: Execução de comando e persistência imediata
- **WHEN** um `QUndoCommand` é empilhado e executado na `QUndoStack`
- **THEN** os dados serializados do comando (`serializar(anonimizado=False)`) são anexados instantaneamente ao arquivo `diario_pendente.bin`.

#### Scenario: Coalescência de Comandos Mesclados sem Invalidação de Cache
- **WHEN** um comando de alteração de texto contínuo é mesclado no topo da pilha pelo `QUndoStack`
- **THEN** o sistema atualiza o diário pendente sem invalidar o cache de comandos anonimizados e sem reler `diario_salvo.bin` do disco.
