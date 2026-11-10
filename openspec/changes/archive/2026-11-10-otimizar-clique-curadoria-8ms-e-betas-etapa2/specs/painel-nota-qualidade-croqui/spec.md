# Spec Delta: painel-nota-qualidade-croqui

## MODIFIED Requirements

### Requirement: Escala Aberta em Três Etapas por Ordens de Grandeza
O sistema SHALL calcular a `nota_qualidade` de um croqui somando os pontos obtidos em tarefas distribuídas em três etapas hierárquicas: Etapa 1 (Essenciais para Publicação, `1000` pontos por tarefa), Etapa 2 (Qualidade, Navegação Offline e Segurança, `100` pontos por tarefa) e Etapa 3 (Lapidação, História e Comunidade, `10` pontos por tarefa).

#### Scenario: Cálculo aditivo entre etapas
- **WHEN** um croqui cumpre integralmente 6 tarefas de `1000` pontos da Etapa 1, 3 tarefas de `100` pontos da Etapa 2 e 4 tarefas de `10` pontos da Etapa 3
- **THEN** a `nota_qualidade` total resultante SHALL ser `6340` pontos.

### Requirement: Critérios da Etapa 2 e Etapa 3
O sistema SHALL avaliar na Etapa 2 (`100` pontos cada): coordenadas de estacionamento e escalada nos setores/grupos ($\ge 90\%$), trilhas de aproximação, extensão e proteções nas vias encordadas ($\ge 90\%$), traçados vetoriais (`LinhaTrajeto`) ou desenhos extraídos nos mapas, destaques nos setores, descrições/betas nas escaladas ($\ge 50\%$), fotos de capa nos setores/grupos ($\ge 90\%$) e vídeos de beta vinculados às escaladas sem candidatos pendentes em `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados`). Na Etapa 3 (`10` pontos cada), SHALL avaliar créditos, conquistadores/data de abertura, tipo de parede, indicadores de família/celular, associação/Pix e flags de revisão.

#### Scenario: Avaliação completa das Etapas 2 e 3
- **WHEN** um croqui preenche gradualmente coordenadas de setores, trilhas, fichas técnicas de vias, vídeos de beta sem pendências de curadoria, créditos e conquistadores
- **THEN** cada critério das Etapas 2 e 3 SHALL somar até `100` e `10` pontos respectivamente à `nota_qualidade` total.

#### Scenario: Detecção de betas pendentes em curadoria_betas na Etapa 2
- **WHEN** um croqui possui vídeos de beta aprovados nas escaladas, mas ainda possui candidatos em `betas_nao_scorados` ou `betas_nao_revisados` dentro de `curadoria_betas`
- **THEN** a tarefa `"Vídeos de beta e curadoria em dia"` na Etapa 2 (`100` pontos) SHALL constar como não concluída (`0` pontos) e exibir a ação rápida `"Revisar betas pendentes"` apontando para `"page:betas"`.
