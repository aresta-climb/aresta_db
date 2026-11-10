# Spec Delta

## MODIFIED Requirements

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
