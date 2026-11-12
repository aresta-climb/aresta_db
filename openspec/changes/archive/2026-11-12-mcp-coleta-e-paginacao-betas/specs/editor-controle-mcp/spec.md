# Spec Delta

## ADDED Requirements

### Requirement: Coleta Assíncrona de Betas em Background via MCP com Persistência Incremental por Micro-Lote
O servidor MCP MUST disponibilizar a ferramenta `aresta_coletar_betas` para gerenciar a coleta multi-fonte de candidatos a beta (`acao`: `"iniciar"`, `"status"` ou `"cancelar"`). A execução das buscas de rede MUST ocorrer integralmente fora da thread principal da interface gráfica (Qt Event Loop), despachando para a thread principal exclusivamente a leitura inicial das escaladas e a gravação atômica de cada micro-lote concluído no histórico (`QUndoStack`) via `CroquiController`. A ferramenta MUST suportar filtragem opcional por `alvo_setor`, `escaladas_uids` e `apenas_sem_coleta` (padrão `True`, ignorando escaladas que já possuam entrada em `curadoria_betas.conteudo` ou betas aprovados), além de *long-polling* limitado por `aguardar_segundos` (máximo `20.0s`) fora da thread principal do Qt, retornando sempre um resumo estruturado leve sem despejar as listas completas de candidatos ou rejeitados.

#### Scenario: Coleta completa rápida dentro da janela de long-polling
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", aguardar_segundos=15)` para um conjunto de escaladas cuja busca termina antes do tempo limite de espera
- **THEN** o servidor executa a busca multi-fonte fora da thread principal do Qt, grava os novos candidatos em `betas_nao_scorados` e os itens auto-filtrados em `betas_rejeitados` via `CroquiController` e retorna imediatamente na mesma chamada `status: "concluido"` com os contadores `total_escaladas`, `escaladas_processadas`, `novos_candidatos_adicionados` e `novos_rejeitados_adicionados`

#### Scenario: Coleta de grande porte (1.000+ vias) com retorno parcial e persistência incremental por micro-lote
- **WHEN** o cliente MCP inicia uma coleta para um croqui com centenas ou milhares de escaladas que excede `aguardar_segundos` e depois consulta `aresta_coletar_betas(acao="status")` ou solicita `aresta_coletar_betas(acao="cancelar")`
- **THEN** a chamada retorna `status: "em_andamento"` dentro do limite de `aguardar_segundos` sem bloquear a UI nem estourar o timeout da ponte MCP, cada micro-lote concluído em segundo plano é gravado incrementalmente em `curadoria_betas.conteudo` via `CroquiController`, e caso a coleta seja cancelada, todo o progresso dos micro-lotes já processados permanece preservado no modelo

#### Scenario: Filtragem automática de escaladas já coletadas com apenas_sem_coleta ativado
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", apenas_sem_coleta=True)` em um croqui onde parte das escaladas já possui entrada em `curadoria_betas.conteudo` (com candidatos ou rejeitados) ou betas publicados em `Escalada.betas`
- **THEN** o sistema ignora as escaladas já coletadas e executa as buscas web exclusivamente para as escaladas ainda sem coleta registrada

### Requirement: Listagem Paginada e Enriquecida de Betas Não Scorados via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_listar_betas_nao_scorados` (aceitando `offset`, `limite` e `alvo_setor` opcionais) que retorna apenas as escaladas que possuem itens pendentes em `betas_nao_scorados`, enriquecidas com os metadados da escalada (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_uid`, `setor_nome`, `pico_nome`, `conquistadores`, `quantidade_betas_nao_revisados`) e omitindo a lista `betas_rejeitados`.

#### Scenario: Paginação de escaladas com betas_nao_scorados em croqui de grande porte
- **WHEN** o cliente MCP chama `aresta_listar_betas_nao_scorados(offset=0, limite=20)` em um croqui contendo centenas de escaladas e milhares de itens em `betas_rejeitados`
- **THEN** o servidor retorna `total_escaladas_pendentes`, `total_candidatos_pendentes`, `offset`, `limite`, `tem_mais` e a fatia de até 20 itens contendo os metadados de cada escalada e sua lista `betas_nao_scorados`, sem incluir `betas_rejeitados` no payload JSON
