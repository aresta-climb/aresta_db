# Spec Delta

## MODIFIED Requirements

### Requirement: Orquestração no Workflow Antigravity
O sistema SHALL disponibilizar duas skills complementares — `.agents/skills/coletar_betas_croqui/SKILL.md` (para coleta multi-fonte em background via `aresta_coletar_betas` suportando croquis de 1.000+ vias) e `.agents/skills/avaliar_betas_croqui/SKILL.md` (para leitura paginada via `aresta_listar_betas_nao_scorados` e pontuação paralela com sub-agentes `AvaliadorBetas`) — operando de forma integrada com o servidor MCP do Editor Aresta e com o campo `curadoria_betas` do `Croqui`.

#### Scenario: Coleta autônoma de betas via MCP em croqui de qualquer porte
- **WHEN** o usuário solicita ao agente conectado via MCP a coleta de betas do croqui (ou de um setor específico) usando a skill `coletar_betas_croqui`
- **THEN** o agente MUST invocar `aresta_coletar_betas(acao="iniciar")`, acompanhar o progresso via `aresta_coletar_betas(acao="status")` (ou agendamento de timer) até que `status` seja `"concluido"`, sem bloquear a UI do Editor Aresta e preservando o progresso incremental em micro-lotes

#### Scenario: Execução orquestrada da avaliação paginada de betas não scorados
- **WHEN** o usuário solicita ao agente conectado via MCP a avaliação dos betas não scorados usando a skill `avaliar_betas_croqui`
- **THEN** o agente MUST consultar as escaladas pendentes de forma paginada com `aresta_listar_betas_nao_scorados` (evitando carregar `betas_rejeitados` ou fazer consultas individuais por escalada), particionar em lotes para sub-agentes `AvaliadorBetas` em paralelo e persistir os itens pontuados em `betas_nao_revisados` via `aresta_alterar_em_lote`
