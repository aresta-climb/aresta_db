# Delta Specification: editor-controle-mcp

## MODIFIED Requirements

### Requirement: Despacho Thread-Safe Qt e Blindagem do Histórico contra Comandos Inválidos
Toda requisição de execução de ferramenta recebida pelo servidor MCP que envolva consulta ou alteração do estado da aplicação (`CroquiModel`, `IndiceUidsModel`, `QUndoStack` ou widgets da interface) MUST ser despachada para a thread principal da interface gráfica do PySide6. O `GerenciadorHistorico` MUST registrar seu slot `_on_index_changed` com `@Slot(int)` e proteger `__getattr__` contra atributos privados/internos. O `CmdAlterarCampo` MUST validar os tipos e rejeitar campos `repeated` sem índice no `__init__` antes de qualquer empilhamento em `QUndoStack`. Para evitar *split-brain* entre cliente MCP e histórico local, o `DespachanteQt` MUST distinguir o tempo limite de espera na fila (`timeout`) do tempo limite máximo de conclusão (`timeout_execucao`): se `timeout` expirar e `futuro.cancel()` retornar `True` (tarefa ainda pendente na fila), MUST cancelar e lançar `TimeoutError` sem mutar o modelo; se `futuro.cancel()` retornar `False` porque a execução já iniciou na thread principal do Qt, MUST aguardar até `timeout_execucao` para retornar o resultado real cometido.

#### Scenario: Execução de comando a partir da thread do servidor MCP
- **WHEN** o cliente MCP invoca uma ferramenta de mutação enquanto o loop de eventos Qt está ativo na thread principal
- **THEN** o despachante encaminha a ação para a thread da GUI via eventos Qt, executa a ação com segurança e retorna o resultado sem travamento ou condições de corrida

#### Scenario: Rejeição fail-fast de campo repeated sem índice ou tipo inválido antes do QUndoStack
- **WHEN** o cliente MCP ou chamador tenta alterar um campo `repeated` sem especificar `.indice` em `CmdAlterarCampo` (ex: `campo="creditos"`) ou envia um valor incompatível com o `FieldDescriptor`
- **THEN** a exceção `ValueError` ou `TypeError` é lançada durante a instanciação do comando antes de `QUndoStack.push`, nenhum comando é empilhado no histórico e o servidor MCP retorna `isError: True` com mensagem descritiva

#### Scenario: Cancelamento limpo quando a fila Qt está bloqueada antes de iniciar a tarefa
- **WHEN** o `DespachanteQt` enfileira uma tarefa que ainda está pendente na fila quando `timeout` expira
- **THEN** `futuro.cancel()` retorna `True`, o despachante lança `TimeoutError` imediatamente e a função nunca é executada quando o loop Qt drena a fila posteriormente

#### Scenario: Prevenção de split-brain quando a execução já iniciou na thread principal do Qt
- **WHEN** uma tarefa já iniciou sua execução na thread principal do Qt, ultrapassa o `timeout` de enfileiramento, mas conclui dentro de `timeout_execucao`
- **THEN** o `DespachanteQt` identifica que `futuro.cancel()` retornou `False`, aguarda a conclusão até `timeout_execucao` e retorna o resultado real cometido sem emitir falso `TimeoutError`

### Requirement: Coleta Assíncrona de Betas em Background via MCP com Persistência Incremental por Micro-Lote
O servidor MCP MUST disponibilizar a ferramenta `aresta_coletar_betas` para gerenciar a coleta multi-fonte de candidatos a beta (`acao`: `"iniciar"`, `"status"` ou `"cancelar"`). A execução das buscas de rede MUST ocorrer integralmente fora da thread principal da interface gráfica (Qt Event Loop), despachando para a thread principal exclusivamente a leitura inicial das escaladas (incluindo `Pico.cidade` e `Croqui.nome`), a reavaliação offline inicial de itens `[Auto-filtrado: ...]` em `betas_rejeitados` via `CroquiController.reavaliar_betas_auto_filtrados`, e a gravação atômica de cada micro-lote concluído no histórico (`QUndoStack`) via `CroquiController`. A ferramenta MUST suportar filtragem opcional por `alvo_setor`, `escaladas_uids` e `apenas_sem_coleta` (padrão `True`, ignorando na busca web escaladas que já possuam entrada em `curadoria_betas.conteudo` ou betas aprovados), ignorar escaladas cujo nome seja placeholder sem requisição de rede, além de *long-polling* limitado por `aguardar_segundos` (máximo `20.0s`) fora da thread principal do Qt, retornando sempre um resumo estruturado leve com `auto_filtrados_promovidos` sem despejar as listas completas de candidatos ou rejeitados.

#### Scenario: Coleta completa rápida dentro da janela de long-polling
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", aguardar_segundos=15)` para um conjunto de escaladas cuja busca termina antes do tempo limite de espera
- **THEN** o servidor reavalia offline itens `[Auto-filtrado: ...]` do escopo, executa a busca multi-fonte fora da thread principal do Qt (propagando `cidade` e `nome_croqui`), grava os novos candidatos em `betas_nao_scorados` e os itens auto-filtrados em `betas_rejeitados` via `CroquiController` e retorna imediatamente na mesma chamada `status: "concluido"` com os contadores `total_escaladas`, `escaladas_processadas`, `novos_candidatos_adicionados`, `novos_rejeitados_adicionados` e `auto_filtrados_promovidos`

#### Scenario: Coleta de grande porte (1.000+ vias) com retorno parcial e persistência incremental por micro-lote
- **WHEN** o cliente MCP inicia uma coleta para um croqui com centenas ou milhares de escaladas que excede `aguardar_segundos` e depois consulta `aresta_coletar_betas(acao="status")` ou solicita `aresta_coletar_betas(acao="cancelar")`
- **THEN** a chamada retorna `status: "em_andamento"` dentro do limite de `aguardar_segundos` sem bloquear a UI nem estourar o timeout da ponte MCP, cada micro-lote concluído em segundo plano é gravado incrementalmente em `curadoria_betas.conteudo` via `CroquiController`, e caso a coleta seja cancelada, todo o progresso dos micro-lotes já processados permanece preservado no modelo

#### Scenario: Filtragem automática de escaladas já coletadas com apenas_sem_coleta ativado
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", apenas_sem_coleta=True)` em um croqui onde parte das escaladas já possui entrada em `curadoria_betas.conteudo` (com candidatos ou rejeitados, inclusive itens `[Auto-filtrado: ...]`) ou betas publicados em `Escalada.betas`
- **THEN** o sistema reavalia offline os auto-filtrados das escaladas do escopo (promovendo os recém-aprovados para `betas_nao_scorados`), contabiliza `auto_filtrados_promovidos` e executa buscas web exclusivamente para as escaladas ainda sem coleta registrada (que não tenham nome placeholder)

## ADDED Requirements

### Requirement: Pontuação Atômica e Enxuta de Betas via MCP (aresta_pontuar_betas)
O servidor MCP MUST disponibilizar `aresta_pontuar_betas`, delegando para `CroquiController.pontuar_betas_em_lote` para promover candidatos de `betas_nao_scorados` para `betas_nao_revisados` recebendo apenas `{escalada_uid, avaliacoes: [{url, llm_confidence_score, llm_reasoning}]}`, preservando metadados e `snippets` em memória em um único `CmdMacro`.

#### Scenario: Pontuação em lote de múltiplas escaladas preservando snippets e ordenação decrescente
- **WHEN** o cliente MCP chama `aresta_pontuar_betas` informando `escalada_uid`, `url`, `llm_confidence_score` (`0..100`) e `llm_reasoning` para candidatos pendentes
- **THEN** o servidor valida todos os UIDs, URLs e scores antecipadamente, promove os candidatos avaliados preservando `midia`, `snippets`, `match_multiplas_fontes` e `match_nome_no_snippet` da RAM, ordena `betas_nao_revisados` em ordem decrescente de score, remove os itens avaliados de `betas_nao_scorados` em um único `CmdMacro` e retorna os contadores atualizados

#### Scenario: Rejeição fail-fast ao receber UID, URL, score ou justificativa inválidos
- **WHEN** `aresta_pontuar_betas` recebe `escalada_uid` inexistente, `url` ausente de `betas_nao_scorados`, `llm_confidence_score` fora de `0..100` (ou booleano) ou `llm_reasoning` vazio em qualquer item
- **THEN** a chamada lança erro antes de empilhar qualquer comando no histórico e o `CroquiModel` permanece inalterado
