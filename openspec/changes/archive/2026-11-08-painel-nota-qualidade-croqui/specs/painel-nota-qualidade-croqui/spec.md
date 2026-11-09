# Spec Delta

## Purpose

Define o motor determinístico de cálculo da `nota_qualidade`, sua persistência no índice compilado (`indice.binarypb`) e o diagnóstico de tarefas de melhoria de croquis em três etapas por ordens de grandeza (`1000`, `100` e `10` pontos) na página primária "Painel" do Editor Aresta.

## ADDED Requirements

### Requirement: Escala Aberta em Três Etapas por Ordens de Grandeza
O sistema SHALL calcular a `nota_qualidade` de um croqui somando os pontos obtidos em tarefas distribuídas em três etapas hierárquicas: Etapa 1 (Essenciais para Publicação, `1000` pontos por tarefa), Etapa 2 (Qualidade, Navegação Offline e Segurança, `100` pontos por tarefa) e Etapa 3 (Lapidação, História e Comunidade, `10` pontos por tarefa).

#### Scenario: Cálculo aditivo entre etapas
- **WHEN** um croqui cumpre integralmente 6 tarefas de `1000` pontos da Etapa 1, 3 tarefas de `100` pontos da Etapa 2 e 4 tarefas de `10` pontos da Etapa 3
- **THEN** a `nota_qualidade` total resultante SHALL ser `6340` pontos.

### Requirement: Pontuação Parcial Proporcional com Meta de 90%
Para critérios avaliados sobre uma coleção de entidades com meta de completude de $90\%$, o sistema SHALL conceder pontos proporcionais à razão `proporcao_atual / 0.90` (limitados ao peso máximo da tarefa e arredondados para inteiro) e considerar a tarefa concluída quando a proporção atingir pelo menos $90\%$.

#### Scenario: Cobertura parcial abaixo da meta de 90%
- **WHEN** uma tarefa de peso `1000` pontos e meta de $90\%$ avalia um croqui onde $45\%$ das escaladas cumprem o critério
- **THEN** o sistema SHALL conceder `500` pontos parciais para a tarefa
- **AND** informar que a conclusão da tarefa adicionará `+500` pontos à `nota_qualidade`.

#### Scenario: Cobertura igual ou superior à meta de 90%
- **WHEN** uma tarefa de peso `1000` pontos e meta de $90\%$ avalia um croqui onde $92\%$ das escaladas cumprem o critério
- **THEN** o sistema SHALL conceder a pontuação máxima de `1000` pontos e marcar a tarefa como concluída.

### Requirement: Regra de Aplicabilidade Automática por Estrutura e Modalidade
Quando uma tarefa avaliar um subconjunto específico de entidades (como múltiplos setores para Mapa Geral ou vias encordadas para extensão e proteções) e o croqui possuir zero entidades aplicáveis àquele subconjunto, o sistema SHALL conceder automaticamente $100\%$ dos pontos da tarefa e marcá-la como concluída.

#### Scenario: Mapa Geral em croqui com apenas um setor
- **WHEN** um croqui possui apenas 1 setor cadastrado e nenhum Mapa Geral configurado no pico
- **THEN** a tarefa de Mapa Geral da Etapa 1 SHALL conceder automaticamente `1000` pontos e constar como concluída.

#### Scenario: Extensão e proteções em croqui exclusivo de Boulders
- **WHEN** um croqui possui apenas escaladas da modalidade `Boulder` e nenhuma via encordada (`ViaEsportiva`, `ViaMovel` ou `ViaMultiplasEnfiadas`)
- **THEN** a tarefa de extensão e proteções de vias da Etapa 2 SHALL conceder automaticamente `100` pontos e constar como concluída.

### Requirement: Critérios da Etapa 1 (Essenciais para Publicação)
O sistema SHALL avaliar na Etapa 1 (`1000` pontos cada): (1) Identidade e capa do croqui (`nome`, `descricao` e `caminho_thumbnail`), (2) Localização e `url_google_maps` nos picos, (3) Instruções de chegada/acesso nos picos, (4) Mapa Geral referenciando $\ge 90\%$ dos setores/grupos, (5) $\ge 90\%$ dos setores com mapa, (6) $\ge 90\%$ das escaladas referenciadas em mapas, e (7) $\ge 90\%$ das escaladas com grau de dificuldade (incluindo `PROJETO` em vias e boulders).

#### Scenario: Grau Projeto contabilizado como grau válido
- **WHEN** uma via ou boulder está classificado com dificuldade `PROJETO`
- **THEN** o avaliador SHALL contabilizar essa escalada como possuindo grau de dificuldade válido na tarefa da Etapa 1.

#### Scenario: Croqui sem picos ou sem escaladas cadastradas
- **WHEN** um croqui ainda não possui pelo menos 1 pico e 1 setor com pelo menos 1 escalada
- **THEN** as tarefas dependentes de picos, setores e escaladas da Etapa 1 SHALL retornar `0` pontos e constar como pendentes.

### Requirement: Critérios da Etapa 2 e Etapa 3
O sistema SHALL avaliar na Etapa 2 (`100` pontos cada): coordenadas de estacionamento e escalada nos setores/grupos ($\ge 90\%$), trilhas de aproximação, extensão e proteções nas vias encordadas ($\ge 90\%$), traçados vetoriais (`LinhaTrajeto`) ou desenhos extraídos nos mapas, destaques nos setores, descrições/betas nas escaladas ($\ge 50\%$) e fotos de capa nos setores/grupos ($\ge 90\%$). Na Etapa 3 (`10` pontos cada), SHALL avaliar créditos, conquistadores/data de abertura, tipo de parede, indicadores de família/celular, vídeos de beta sem pendências, associação/Pix e flags de revisão.

#### Scenario: Avaliação completa das Etapas 2 e 3
- **WHEN** um croqui preenche gradualmente coordenadas de setores, trilhas, fichas técnicas de vias, créditos e conquistadores
- **THEN** cada critério das Etapas 2 e 3 SHALL somar até `100` e `10` pontos respectivamente à `nota_qualidade` total.

### Requirement: Exibição em Cascata de Etapas Colapsáveis no Painel
A página "Painel" SHALL exibir as três etapas em seções colapsáveis (expandos) que se abrem em cascata automática conforme o progresso: a primeira etapa que ainda possuir tarefas pendentes SHALL iniciar expandida, enquanto as etapas anteriores já $100\%$ concluídas e as etapas posteriores SHALL iniciar recolhidas, permitindo expansão manual pelo usuário a qualquer momento.

#### Scenario: Transição automática da Etapa 1 para a Etapa 2
- **WHEN** o usuário conclui a última tarefa pendente da Etapa 1
- **THEN** a seção da Etapa 1 SHALL recolher-se automaticamente exibindo o selo de etapa concluída
- **AND** a seção da Etapa 2 SHALL expandir-se automaticamente exibindo suas tarefas.

#### Scenario: Transição automática da Etapa 2 para a Etapa 3
- **WHEN** a Etapa 1 e a Etapa 2 estão $100\%$ concluídas
- **THEN** as Etapas 1 e 2 SHALL apresentar-se recolhidas e a Etapa 3 SHALL apresentar-se expandida.

### Requirement: Ações Rápidas de Navegação Direta por Tarefa
Cada tarefa pendente exibida no Painel SHALL informar o ganho potencial de pontos (ex: `+500 pts`) e disponibilizar botões de ação rápida que emitam a URI de contexto correspondente (`ContextoUIPath`) para navegar diretamente ao formulário na aba "Dados" ou ao mapa correspondente na aba "Mapas".

#### Scenario: Clique em ação rápida para editar setor na aba Dados
- **WHEN** o usuário clica no botão de ação rápida de uma tarefa que aponta para um setor sem coordenadas
- **THEN** o editor SHALL alternar para a aba "Dados" e selecionar diretamente o nó do respectivo setor na árvore de navegação.

#### Scenario: Clique em ação rápida para abrir mapa na aba Mapas
- **WHEN** o usuário clica no botão de ação rápida de uma tarefa de mapeamento de vias de um setor
- **THEN** o editor SHALL alternar para a aba "Mapas" e selecionar diretamente o mapa do respectivo setor.

### Requirement: Controle Client-Side de Publicação no Painel via Histórico
O cabeçalho do Painel SHALL exibir e controlar o estado de publicação do croqui (`publicar_croqui`) através de comandos na pilha global de histórico (`QUndoCommand`), habilitando a transição de `Rascunho` (`false`) para `Publicado` (`true`) exclusivamente quando $100\%$ das tarefas da Etapa 1 estiverem concluídas, sem bloquear o envio de Pull Requests de rascunho no botão "Propor Mudança".

#### Scenario: Croqui em rascunho com Etapa 1 incompleta
- **WHEN** o croqui está com `publicar_croqui = false` e possui pelo menos uma tarefa pendente na Etapa 1
- **THEN** a ação de marcar como `Publicado` no Painel SHALL permanecer desabilitada com mensagem orientando concluir a Etapa 1
- **AND** o botão global "Propor Mudança" na barra superior SHALL permanecer habilitado para envio de Pull Request como rascunho.

#### Scenario: Ativação de publicação após concluir a Etapa 1 com Undo/Redo
- **WHEN** todas as tarefas da Etapa 1 estão concluídas e o usuário aciona o botão para marcar o croqui como `Publicado` no Painel
- **THEN** o sistema SHALL empilhar um comando no histórico alterando `publicar_croqui` para `true`
- **AND** acionar Desfazer (Undo) SHALL reverter `publicar_croqui` para `false` atualizando o Painel.

#### Scenario: Croqui legado já publicado com pendências na Etapa 1
- **WHEN** um croqui carregado já possui `publicar_croqui = true`, mas apresenta tarefas incompletas na Etapa 1
- **THEN** o sistema SHALL preservar `publicar_croqui = true` sem despublicá-lo automaticamente, exibir aviso de pendências básicas no cabeçalho do Painel e manter a Etapa 1 expandida.

### Requirement: Pré-computação da Nota de Qualidade do Croqui no Índice
O pipeline de compilação e deploy do índice SHALL calcular a `nota_qualidade` de cada croqui publicado através do motor de avaliação e gravar o valor inteiro resultante no campo `resumo.precomputados.nota_qualidade` do `indice.binarypb`, refletindo-o também em `indice.yaml` e no relatório de saúde `STATUS_CROQUIS.md`.

#### Scenario: Compilação do índice com nota_qualidade pré-computada
- **WHEN** o pipeline de deploy gera os croquis e monta o `indice.binarypb`
- **THEN** cada `ResumoCroqui` no índice possui `precomputados.nota_qualidade` preenchido com a pontuação inteira calculada pelo avaliador de qualidade para aquele croqui.

#### Scenario: Reflexão de nota_qualidade no arquivo indice.yaml
- **WHEN** o arquivo `indice.yaml` é exportado para inspeção e depuração
- **THEN** a chave `nota_qualidade` está presente sob a seção `precomputados` de cada croqui com o respectivo valor numérico.

#### Scenario: Exibição da nota_qualidade no relatório STATUS_CROQUIS.md
- **WHEN** o relatório de saúde dos croquis (`STATUS_CROQUIS.md`) é gerado
- **THEN** a tabela Markdown inclui a coluna `Nota Qualidade` exibindo a pontuação calculada para cada croqui da base.
