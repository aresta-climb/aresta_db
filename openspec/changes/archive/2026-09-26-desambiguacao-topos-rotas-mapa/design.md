## Context

Ver `proposal.md` para motivação e antecedentes do problema. O sistema atual possui o módulo [`editor/core/topologia_trajeto.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/topologia_trajeto.py), responsável pelas regras puras de cálculo geométrico e semântico dos traçados. Dentro dele, a função `desambiguar_topos(linhas, referencias)` é chamada por `MapasController.adicionar_rota_com_tracado` após qualquer criação de rota no mapa.

Atualmente, `desambiguar_topos` verifica apenas se `len(rotas) > 1`. Quando há mais de uma rota no mapa, a função assume erroneamente que todas as rotas são variantes ou compartilham topos, atribuindo letras sequenciais (`A`, `B`, `C`...) para o último nó de todas as rotas indistintamente.

## Goals / Non-Goals

**Goals:**
- Implementar análise relacional de rotas em `desambiguar_topos` para distinguir rotas isoladas de rotas que realmente necessitam de desambiguação no topo.
- Garantir que um nó final de rota só receba `FIM_TOP` com letra se:
  1. Compartilhar o ponto final com outra rota (convergência de topos).
  2. Compartilhar início ou trecho de traçado com outra rota que termine em ponto final diferente (bifurcação / dois finais para um mesmo início).
- Garantir que rotas isoladas (sem junção ou separação com nenhuma outra rota) permaneçam com o nó final como `PASSAGEM` sem rótulo textual.
- Garantir comportamento idempotente e reversível: se uma variante for desfeita ou removida, a rota remanescente deve voltar a ter o topo limpo sem letras residuais.
- Manter 100% de cobertura de testes unitários e de integração conforme os Princípios III, IV e V de `AGENTS.md`.

**Non-Goals:**
- Não alterar a estrutura de dados Protobuf (`croqui.proto`).
- Não alterar a lógica de inícios numéricos (`1`, `2`, `1, 2`), que já opera corretamente com escopo de setor.
- Não alterar linhas avulsas que não estejam associadas a referências de escaladas.

## Decisions

### Decisão 1: Análise Relacional Direta de Conectividade em `desambiguar_topos`
- **Escolha**: Para cada referência válida no mapa, coletamos:
  - `coord_inicio`: coordenada $(x, y)$ do primeiro nó da primeira linha.
  - `coord_fim`: coordenada $(x, y)$ do último nó da última linha.
  - `linhas_ids`: conjunto de IDs de linhas da referência.
  - `pontos`: conjunto de todas as coordenadas $(x, y)$ dos nós de todas as linhas da referência.
  - `ultimo_no`: referência direta ao objeto `NoTrajeto` final.
  
  Um ponto final `coord_fim` requer desambiguação se, e somente se, para a rota $i$:
  - **Convergência**: Existe outra rota $j \neq i$ com `coord_fim_j == coord_fim_i`.
  - **Bifurcação / Separação**: Existe outra rota $j \neq i$ com `coord_fim_j != coord_fim_i` e que compartilha pontos ou linhas (`coord_inicio_i == coord_inicio_j` ou `linhas_ids_i & linhas_ids_j` ou `pontos_i & pontos_j`).

- **Racional**: Esta abordagem é declarativa, de alta legibilidade, puramente matemática e mapeia 1:1 os dois únicos casos onde letras no topo fazem sentido na escalada. Evita complexidade desnecessária de bibliotecas de grafos externas.
- **Alternativas consideradas**:
  - *Agrupamento em componentes conexos via busca em profundidade (DFS)*: embora válida, a checagem explícita de `compartilha_fim` e `tem_bifurcacao` é mais direta e expressa a regra de negócio de forma autoexplicativa.

### Decisão 2: Limpeza Automática e Idempotência
- **Escolha**: Nós finais cujas coordenadas não necessitem de desambiguação têm seu tipo definido estritamente como `croqui_pb2.NoTrajeto.TipoNo.PASSAGEM` e `rotulo = ""`.
- **Racional**: Garante que o estado seja determinístico. Se uma via tinha Top "A" porque existia uma Variante "B", e o usuário apaga ou dá Undo na variante, reexecutar `desambiguar_topos` restaura o topo da via original para passagem limpa sem deixar "A" órfão.

### Decisão 3: Atribuição Sequencial Estável de Letras
- **Escolha**: As coordenadas que necessitam de desambiguação são processadas na ordem estável em que aparecem na lista de referências do mapa, consumindo letras de `obter_proxima_letra_top` (`A`, `B`, `C`...).
- **Racional**: Preserva estabilidade na ordenação e garante que rotas que convergem no mesmo topo compartilhem rigorosamente a mesma letra.

## Risks / Trade-offs

- **[Precisão geométrica de nós compartilhados]** → *Mitigação*: Como as alças e nós de traçado no editor utilizam coordenadas inteiras de pixels e a ferramenta de snap magnetiza com precisão exata nas coordenadas do nó existente, a comparação de tuplas inteiras `(int(no.x), int(no.y))` é determinística e imune a imprecisões de ponto flutuante.
