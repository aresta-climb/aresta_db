# painel-nota-qualidade-croqui Specification

## Purpose

Define o motor determinístico de cálculo da `nota_qualidade`, sua persistência no índice compilado (`indice.binarypb`) e o diagnóstico de tarefas de melhoria de croquis em três etapas por ordens de grandeza (`1000`, `100` e `10` pontos) na página primária "Painel" do Editor Aresta.

## Requirements

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
O sistema SHALL avaliar na Etapa 1 (`1000` pontos cada): (1) Identidade e capa do croqui (`nome`, `descricao` e `caminho_thumbnail`), (2) Localização e `url_google_maps` nos picos, (3) Instruções de chegada/acesso nos picos, (4) Mapa Geral referenciando $\ge 90\%$ dos setores/grupos, (5) $\ge 90\%$ dos setores com mapa, (6) $\ge 90\%$ das escaladas referenciadas em mapas, (7) $\ge 90\%$ das escaladas com grau de dificuldade (incluindo `PROJETO` em vias e boulders), e (8) Mapa de pontos de estrada dos picos (`etapa1_malha_estrada_picos`), concedendo `1000` pontos (`concluida = true`) quando todos os picos possuem malha atualizada na `VERSAO_ATUAL_MALHA_ESTRADA` (`2`), `700` pontos parciais por pico (`concluida = false`, com ação `"Atualizar mapa de pontos"`) quando a malha está sincronizada com a coordenada e possui `duracao_minutos` mas tem `versao < 2`, e `0` pontos (`concluida = false`, com ação `"Gerar mapa de pontos"`) quando ausente ou com coordenada divergente.

#### Scenario: Grau Projeto contabilizado como grau válido
- **WHEN** uma via ou boulder está classificado com dificuldade `PROJETO`
- **THEN** o avaliador SHALL contabilizar essa escalada como possuindo grau de dificuldade válido na tarefa da Etapa 1.

#### Scenario: Croqui sem picos ou sem escaladas cadastradas
- **WHEN** um croqui ainda não possui pelo menos 1 pico e 1 setor com pelo menos 1 escalada
- **THEN** as tarefas dependentes de picos, setores e escaladas da Etapa 1 SHALL retornar `0` pontos e constar como pendentes.

#### Scenario: Mapa de pontos de estrada em versão anterior concede 700 pontos e permanece pendente
- **WHEN** um croqui possui um pico com `malha_estrada` sincronizada com `localizacao` e com `duracao_minutos`, mas com `versao < 2`
- **THEN** a tarefa `etapa1_malha_estrada_picos` SHALL conceder `700` de `1000` pontos (`ganho_potencial = 300`), constar com `concluida = false` e disponibilizar a ação `"Atualizar mapa de pontos"`.

### Requirement: Critérios da Etapa 2 e Etapa 3
O sistema SHALL avaliar na Etapa 2 (`100` pontos cada): coordenadas de estacionamento e escalada nos setores/grupos ($\ge 90\%$), trilhas de aproximação, extensão e proteções nas vias encordadas ($\ge 90\%$), traçados vetoriais (`LinhaTrajeto`) ou desenhos extraídos nos mapas, destaques nos setores, descrições/betas nas escaladas ($\ge 50\%$), fotos de capa nos setores/grupos ($\ge 90\%$) e vídeos de beta vinculados às escaladas sem candidatos pendentes em `curadoria_betas` (`betas_nao_scorados` e `betas_nao_revisados`). Na Etapa 3 (`10` pontos cada), SHALL avaliar créditos, conquistadores/data de abertura, tipo de parede, indicadores de família/celular, associação/Pix e flags de revisão.

#### Scenario: Avaliação completa das Etapas 2 e 3
- **WHEN** um croqui preenche gradualmente coordenadas de setores, trilhas, fichas técnicas de vias, vídeos de beta sem pendências de curadoria, créditos e conquistadores
- **THEN** cada critério das Etapas 2 e 3 SHALL somar até `100` e `10` pontos respectivamente à `nota_qualidade` total.

#### Scenario: Detecção de betas pendentes em curadoria_betas na Etapa 2
- **WHEN** um croqui possui vídeos de beta aprovados nas escaladas, mas ainda possui candidatos em `betas_nao_scorados` ou `betas_nao_revisados` dentro de `curadoria_betas`
- **THEN** a tarefa `"Vídeos de beta e curadoria em dia"` na Etapa 2 (`100` pontos) SHALL constar como não concluída (`0` pontos) e exibir a ação rápida `"Revisar betas pendentes"` apontando para `"page:betas"`.

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
Cada tarefa pendente exibida no Painel SHALL informar o ganho potencial de pontos (ex: `+500 pts`) e disponibilizar botões de ação rápida com verbos imperativos diretos (sem o prefixo `"Ir para: "`) que emitam a URI de contexto correspondente (`ContextoUIPath`), incluindo o sufixo `/campo:<nome_campo>` quando a pendência referir-se a um campo ou seção específica do formulário na aba "Dados", ou apontando para o mapa/aba correspondente nas abas "Mapas" e "Betas".
- **Desmembramento por Campo Pendente**: Quando uma tarefa avaliar múltiplos campos independentes de uma mesma entidade (como `nome`, `descricao` e `caminho_thumbnail` no croqui; `localizacao` e `url_google_maps` nos picos; `localizacao_estacionamento` e `localizacao_escalada` nos setores; extensão e proteções nas vias; associação e chave Pix nos picos; ou `revisado_manualmente` e `revisado_bounding_circle` no croqui), o avaliador SHALL gerar uma ação específica para cada campo efetivamente pendente com o respectivo sufixo `/campo:<nome_campo>`.
- **Omissão do Nome do Pico em Croqui de Pico Único**: Nas tarefas avaliadas por pico (localização/Google Maps, instruções de acesso, Mapa Geral, malha de pontos de estrada e associação/Pix), os rótulos das ações SHALL omitir o sufixo `(<Nome do Pico>)` quando o croqui possuir apenas 1 pico cadastrado (ex: `"Adicionar localização"`, `"Adicionar link Google Maps"`), e SHALL incluir `(<Nome do Pico>)` quando o croqui possuir 2 ou mais picos.
- **Navegação ao Campo de Destaque em Setores**: Na tarefa de escaladas de destaque nos setores (Etapa 2), quando um setor com escaladas não possuir nenhuma escalada marcada como destaque, a ação rápida SHALL apontar diretamente para o campo `destaque` da primeira escalada do setor (`.../expando:escaladas/item:0/campo:destaque`).

#### Scenario: Ações desmembradas de localização e Google Maps em croqui com um único pico
- **WHEN** um croqui possui apenas 1 pico (`"Gruta da Lapinha"`) sem coordenadas geográficas e sem `url_google_maps`
- **THEN** a tarefa de localização dos picos SHALL disponibilizar os botões `"Adicionar localização"` (com URI terminando em `/expando:picos/item:0/campo:localizacao`) e `"Adicionar link Google Maps"` (com URI terminando em `/expando:picos/item:0/campo:url_google_maps`), exibidos no card sem o prefixo `"Ir para: "`.

#### Scenario: Ações de pico em croqui com múltiplos picos
- **WHEN** um croqui possui 2 picos (`"Pico Norte"` e `"Pico Sul"`) e ambos estão sem `url_google_maps`
- **THEN** os botões de ação SHALL identificar cada pico no rótulo (`"Adicionar link Google Maps (Pico Norte)"` e `"Adicionar link Google Maps (Pico Sul)"`).

#### Scenario: Clique em ação rápida para editar setor na aba Dados
- **WHEN** o usuário clica no botão `"Adicionar estacionamento (Setor Principal)"` de uma tarefa da Etapa 2
- **THEN** o editor SHALL alternar para a aba "Dados", selecionar o nó do setor na árvore e posicionar o formulário com scroll e foco diretamente no campo `localizacao_estacionamento`.

#### Scenario: Clique em ação rápida para escolher destaque em um setor
- **WHEN** um setor possui escaladas cadastradas mas nenhuma marcada com `destaque = true` e o usuário aciona o botão `"Escolher destaque em <Setor>"`
- **THEN** o editor SHALL navegar para a primeira escalada daquele setor na aba "Dados" e focar diretamente no campo `destaque`.

#### Scenario: Clique em ação rápida para abrir mapa na aba Mapas
- **WHEN** o usuário clica no botão de ação rápida de uma tarefa de mapeamento de escaladas ou desenho de linhas vetoriais de um setor que já possui mapa
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
