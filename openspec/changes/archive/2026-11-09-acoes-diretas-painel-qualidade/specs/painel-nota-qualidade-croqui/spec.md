## MODIFIED Requirements

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
