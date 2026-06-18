## ADDED Requirements

### Requirement: Orquestração do Workflow de PDF
O sistema MUST orquestrar todo o processo de conversão de um PDF de croqui, gerenciando as transições de fase e checagem de estado sem depender de chamadas manuais sequenciais do usuário.

#### Scenario: Início de um novo PDF
- **WHEN** o usuário inicia o workflow apontando para um novo croqui que ainda não possui `partes.json`
- **THEN** o agente orquestrador dispara a Fase 1 para separar as páginas, em seguida pausa a execução apresentando um checkpoint ao usuário

#### Scenario: Retomada de um processamento já iniciado (Fase 2)
- **WHEN** o usuário inicia o workflow apontando para um croqui que já possui `partes.json` validado
- **THEN** o agente orquestrador pula a Fase 1 e invoca sub-agentes paralelos para gerar os arquivos Markdown baseados no json

#### Scenario: Retomada de um processamento na Fase 3
- **WHEN** o usuário inicia o workflow apontando para um croqui que já possui o `compilado.md` e a fase 2 concluída
- **THEN** o agente orquestrador pula as fases 1 e 2, invocando sub-agentes para processamento de mapas.

### Requirement: Execução de Sub-Agentes de Forma Paralela
O sistema MUST utilizar a infraestrutura `define_subagent` e `invoke_subagent` para encapsular os trabalhos que exigem contexto especializado e lançá-los simultaneamente para otimizar tempo.

#### Scenario: Conversão de múltiplos setores
- **WHEN** existem 10 partes apontando para arquivos `.pdf` diferentes no `partes.json`
- **THEN** o orquestrador invoca 10 instâncias simultâneas do sub-agente `ConversorMarkdown`, aguardando a conclusão de todos.

### Requirement: Mecanismo de Auto-Correção (Auto-heal)
O sistema MUST identificar se um sub-agente retornou falha estrutural, sem interromper imediatamente a orquestração de outras partes válidas.

#### Scenario: Falha inicial de um sub-agente
- **WHEN** um sub-agente falha na extração de Markdown de um PDF
- **THEN** o agente orquestrador lê o erro, inicia uma nova instância de sub-agente focada apenas naquela parte (retry), passando o log de erro para auto-correção.

#### Scenario: Esgotamento do limite de auto-correção
- **WHEN** a auto-correção falha por 3 vezes consecutivas na mesma tarefa
- **THEN** o orquestrador isola o erro, aguarda as threads restantes terminarem, pausa a execução geral e apresenta o problema ao usuário para intervenção manual.
