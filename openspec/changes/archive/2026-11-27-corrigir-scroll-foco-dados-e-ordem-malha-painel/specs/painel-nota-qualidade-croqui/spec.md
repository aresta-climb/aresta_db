# Spec Delta

## MODIFIED Requirements

### Requirement: Critérios da Etapa 1 (Essenciais para Publicação)
O sistema SHALL avaliar na Etapa 1 (`1000` pontos cada), nesta ordem: (1) Identidade e capa do croqui (`nome`, `descricao` e `caminho_thumbnail`), (2) Localização e `url_google_maps` nos picos, (3) Mapa de pontos de estrada dos picos (`etapa1_malha_estrada_picos`), (4) Instruções de chegada/acesso nos picos, (5) Mapa Geral referenciando $\ge 90\%$ dos setores/grupos, (6) $\ge 90\%$ dos setores com mapa, (7) $\ge 90\%$ das escaladas referenciadas em mapas, e (8) $\ge 90\%$ das escaladas com grau de dificuldade (incluindo `PROJETO` em vias e boulders). Para `etapa1_malha_estrada_picos`, o sistema SHALL conceder `1000` pontos (`concluida = true`) quando todos os picos possuem malha atualizada na `VERSAO_ATUAL_MALHA_ESTRADA` (`2`), `700` pontos parciais por pico (`concluida = false`, com ação `"Atualizar mapa de pontos"` apontando para `.../campo:malha_estrada`) quando a malha está sincronizada com a coordenada e possui `duracao_minutos` mas tem `versao < 2`, e `0` pontos (`concluida = false`, com ação `"Gerar mapa de pontos"` apontando para `.../campo:malha_estrada` quando o pico já possui coordenada válida, ou `"Adicionar localização"` apontando para `.../campo:localizacao` quando ausente).

#### Scenario: Grau Projeto contabilizado como grau válido
- **WHEN** uma via ou boulder está classificado com dificuldade `PROJETO`
- **THEN** o avaliador SHALL contabilizar essa escalada como possuindo grau de dificuldade válido na tarefa da Etapa 1.

#### Scenario: Croqui sem picos ou sem escaladas cadastradas
- **WHEN** um croqui ainda não possui pelo menos 1 pico e 1 setor com pelo menos 1 escalada
- **THEN** as tarefas dependentes de picos, setores e escaladas da Etapa 1 SHALL retornar `0` pontos e constar como pendentes.

#### Scenario: Mapa de pontos de estrada em versão anterior concede 700 pontos e permanece pendente
- **WHEN** um croqui possui um pico com `malha_estrada` sincronizada com `localizacao` e com `duracao_minutos`, mas com `versao < 2`
- **THEN** a tarefa `etapa1_malha_estrada_picos` SHALL conceder `700` de `1000` pontos (`ganho_potencial = 300`), constar com `concluida = false` e disponibilizar a ação `"Atualizar mapa de pontos"` com URI terminando em `/campo:malha_estrada`.

#### Scenario: Posição da tarefa de mapa de pontos de estrada logo após localização dos picos
- **WHEN** o diagnóstico da Etapa 1 é gerado para o Painel de Qualidade e exportado para o relatório de saúde (`STATUS_CROQUIS.md`)
- **THEN** a tarefa `etapa1_malha_estrada_picos` SHALL figurar na 3ª posição (`1.3 Malha Estrada`), imediatamente após `etapa1_localizacao_picos` (`1.2 Localização e Maps`), mantendo as colunas subsequentes numeradas sequencialmente de `1.4` a `1.8`.

### Requirement: Ações Rápidas de Navegação Direta por Tarefa
Cada tarefa pendente exibida no Painel SHALL informar o ganho potencial de pontos (ex: `+500 pts`) e disponibilizar botões de ação rápida com verbos imperativos diretos (sem o prefixo `"Ir para: "`) que emitam a URI de contexto correspondente (`ContextoUIPath`), incluindo o sufixo `/campo:<nome_campo>` quando a pendência referir-se a um campo ou seção específica do formulário na aba "Dados", ou apontando para o mapa/aba correspondente nas abas "Mapas" e "Betas".
- **Desmembramento por Campo Pendente**: Quando uma tarefa avaliar múltiplos campos independentes de uma mesma entidade (como `nome`, `descricao` e `caminho_thumbnail` no croqui; `localizacao` e `url_google_maps` nos picos; `localizacao_estacionamento` e `localizacao_escalada` nos setores; extensão e proteções nas vias; associação e chave Pix nos picos; ou `revisado_manualmente` e `revisado_bounding_circle` no croqui), o avaliador SHALL gerar uma ação específica para cada campo efetivamente pendente com o respectivo sufixo `/campo:<nome_campo>`. Quando apenas `url_google_maps` estiver pendente no pico, a tarefa `etapa1_localizacao_picos` SHALL exibir apenas `"Adicionar link Google Maps"`.
- **Omissão do Nome do Pico em Croqui de Pico Único**: Nas tarefas avaliadas por pico (localização/Google Maps, instruções de acesso, Mapa Geral, malha de pontos de estrada e associação/Pix), os rótulos das ações SHALL omitir o sufixo `(<Nome do Pico>)` quando o croqui possuir apenas 1 pico cadastrado (ex: `"Adicionar localização"`, `"Adicionar link Google Maps"`, `"Gerar mapa de pontos"`), e SHALL incluir `(<Nome do Pico>)` quando o croqui possuir 2 ou mais picos.
- **Navegação ao Campo de Destaque em Setores**: Na tarefa de escaladas de destaque nos setores (Etapa 2), quando um setor com escaladas não possuir nenhuma escalada marcada como destaque, a ação rápida SHALL apontar diretamente para o campo `destaque` da primeira escalada do setor (`.../expando:escaladas/item:0/campo:destaque`).

#### Scenario: Ações desmembradas de localização e Google Maps em croqui com um único pico
- **WHEN** um croqui possui apenas 1 pico (`"Gruta da Lapinha"`) sem coordenadas geográficas e sem `url_google_maps`
- **THEN** a tarefa de localização dos picos SHALL disponibilizar os botões `"Adicionar localização"` (com URI terminando em `/expando:picos/item:0/campo:localizacao`) e `"Adicionar link Google Maps"` (com URI terminando em `/expando:picos/item:0/campo:url_google_maps`), exibidos no card sem o prefixo `"Ir para: "`.

#### Scenario: Ações de pico em croqui com múltiplos picos
- **WHEN** um croqui possui 2 picos (`"Pico Norte"` e `"Pico Sul"`) e ambos estão sem `url_google_maps`
- **THEN** os botões de ação SHALL identificar cada pico no rótulo (`"Adicionar link Google Maps (Pico Norte)"` e `"Adicionar link Google Maps (Pico Sul)"`).

#### Scenario: Clique em ação rápida para gerar ou atualizar mapa de pontos de estrada
- **WHEN** um pico possui `localizacao` válida mas está sem malha atualizada e o usuário clica em `"Gerar mapa de pontos"` (ou `"Atualizar mapa de pontos"`)
- **THEN** o Painel SHALL emitir a URI `page:dados/node:root/node:Croqui/expando:picos/item:<idx>/campo:malha_estrada` para que a aba "Dados" role até o card `localizacao` do pico e foque diretamente no botão `"Gerar Mapa de Pontos"`.

#### Scenario: Clique em ação rápida para editar setor na aba Dados
- **WHEN** o usuário clica no botão `"Adicionar estacionamento (Setor Principal)"` de uma tarefa da Etapa 2
- **THEN** o editor SHALL alternar para a aba "Dados", selecionar o nó do setor na árvore e posicionar o formulário com scroll e foco diretamente no campo `localizacao_estacionamento`.

#### Scenario: Clique em ação rápida para escolher destaque em um setor
- **WHEN** um setor possui escaladas cadastradas mas nenhuma marcada com `destaque = true` e o usuário aciona o botão `"Escolher destaque em <Setor>"`
- **THEN** o editor SHALL navegar para a primeira escalada daquele setor na aba "Dados" e focar diretamente no campo `destaque`.

#### Scenario: Clique em ação rápida para abrir mapa na aba Mapas
- **WHEN** o usuário clica no botão de ação rápida de uma tarefa de mapeamento de escaladas ou desenho de linhas vetoriais de um setor que já possui mapa
- **THEN** o editor SHALL alternar para a aba "Mapas" e selecionar diretamente o mapa do respectivo setor.
