# Design Técnico: Estilização Visual de Traçados e Marcadores no Padrão Ouroboulder

## Context

O sistema atual de traçados vetoriais foi introduzido para permitir desenho manual de vias e boulders sobre imagens limpas da rocha. Conforme detalhado em `proposal.md`, os círculos de marcação atuais utilizam borda branca grossa e preenchimento permanente na cor da via, o que gera poluição visual quando múltiplos traçados estão visíveis simultaneamente. 

A referência visual do croqui Ouroboulder demonstra que marcadores em repouso com fundo preto e contorno escuro sutil, combinados com destaque colorido sob seleção e linhas em amarelo fluorescente de alto contraste, oferecem uma experiência de leitura muito superior em celulares na falésia.

## Goals / Non-Goals

**Goals:**
- Unificar a identidade visual de traçados e marcadores entre o Editor desktop (`AlcaNoTrajeto`) e o App Flutter (`MarkerPainter`) com fidelidade estética 1:1.
- Adotar o amarelo fluorescente (`#FFD600`) como cor padrão para novos traçados de vias e boulders.
- Redesenhar os círculos identificadores:
  - Eliminar a borda branca interna espessa.
  - Adotar contorno preto fino (1.0px a 1.5px) idêntico ao casing dos tracejados.
  - Fundo preto neutro (`#1A1A1A`) em estado de repouso (não selecionado) com símbolo em branco.
  - Fundo na cor da via (amarelo ou cor personalizada) com halo difuso quando a via ou nó estiver selecionado.
  - Ampliar a escala tipográfica para ocupar 75% a 80% do diâmetro útil do círculo, com peso bold pesado.
- Introduzir o tipo de nó `SETA_DIRECIONAL` (enum 12) no Protobuf, permitindo marcar dinâmicos, botes e direções de travessia orientados pela tangente do spline.
- Manter 100% de cobertura de testes unitários e testes de integração prévios (TDD).

**Non-Goals:**
- Não alterar as geometrias legadas de POI de área (`circulo`, `poligono`, `retangulo`), preservando compatibilidade total com os 400+ croquis existentes.
- Não alterar a formulação matemática da Spline Catmull-Rom ($\alpha = 0.5$) em `spline_catmull_rom.py`, apenas consumir o vetor de ângulos tangentes para orientar as novas setas direcionais.

## Decisions

### Decisão 1: Estados Visuais dos Círculos (Repouso Preto vs. Destaque Colorido)
- **Escolha**:
  - **Repouso**: Fundo `#1A1A1A` (preto carvão fosco), texto branco, contorno preto sutil (1px).
  - **Selecionado**: Fundo com a cor da via (amarelo `#FFD600` por padrão), texto branco, contorno fino e halo suave de seleção.
- **Alternativas consideradas**:
  - *Manter cor da via em repouso e apenas aumentar tamanho ao selecionar*: Rejeitado porque polui visualmente o bloco de pedra quando há 5 ou mais vias vizinhas.
  - *Usar círculos transparentes com borda colorida*: Rejeitado porque letras finas sobre textura de rocha perdem legibilidade imediata sob a luz do sol.
- **Justificativa**: O padrão Ouroboulder foca a atenção cognitiva exclusivamente na via em que o escalador está interessado, deixando as demais discretas como referência contextual.

### Decisão 2: Eliminação da Borda Branca e Ampliação Tipográfica
- **Escolha**: Remover a camada `borderPaint` (branca de 1.5px–2.0px). Calcular a altura da fonte baseando-se no raio útil livre: `tamanho_fonte = raio * 1.35`.
- **Justificativa**: A borda branca grossa estrangulava a área útil interna, forçando a tipografia a ficar minúscula (8px). Sem a borda, o símbolo ganha destaque imediato, mantendo o círculo compacto.

### Decisão 3: Amarelo (`#FFD600`) como Cor Padrão de Traçado
- **Escolha**: Mudar o valor padrão em `ItemTrajetoLinha`, `MapasController` e `ConstrutorCaminhoTrajeto` de `#FF6D00` (laranja) para `#FFD600` (amarelo ouro).
- **Justificativa**: O amarelo possui o maior contraste de luminância (canal Y no espaço YUV/Lab) contra rochas graníticas cinzas, calcários escuros e sombras de tetos/fendas, exatamente como comprovado historicamente nos croquis do Ouroboulder e guias internacionais.

### Decisão 4: Tipo de Nó `SETA_DIRECIONAL` no Protobuf
- **Escolha**: Adicionar `SETA_DIRECIONAL = 12` em `NoTrajeto.TipoNo` e calcular a orientação geométrica através do ângulo tangente da spline (`angulo_graus_x100`) durante a compilação em `MarcadorCompilado`.
- **Justificativa**: Atende ao Princípio II (Library-First) e Princípio I (Tudo em Português). Permite que o autor do croqui insira setas de dinâmico ou botes sem precisar desenhar gambiarras visuais ou quebrar a linha em múltiplos trechos.

## Risks / Trade-offs

- **[Risco: Círculos pretos em repouso sobre fendas muito escuras ou sombras profundas]** → *Mitigação:* O casing externo sutil de 1px possui leve luminosidade/contraste ou sombra suave para garantir que o círculo preto seja distinguível mesmo sobre sombras pretas.
- **[Risco: Dessincronização entre Editor e App]** → *Mitigação:* As constantes de proporção tipográfica e lógica de seleção são replicadas exatamente em ambos os projetos, cobertas por testes automatizados em Python (`widget_editor_mapas_test.py`) e Flutter (`mapa_interativo_test.dart`).

## Migration Plan

1. Adicionar `SETA_DIRECIONAL = 12` em `aresta_api/proto/croqui.proto`.
2. Recompilar stubs Protobuf para Python (`build.py protos`) e Dart.
3. Atualizar `editor/views/widget_editor_mapas.py` (`AlcaNoTrajeto` e `ItemTrajetoLinha`):
   - Remover borda branca, adicionar fundo preto em repouso e amarelo padrão.
   - Suporte a seleção com highlight e renderização de `SETA_DIRECIONAL`.
4. Atualizar `scripts/preparar_submissao_lib.py` para pré-calcular e compilar marcadores de `SETA_DIRECIONAL`.
5. Atualizar `aresta_app/frontend/lib/pages/mapa_interativo.dart` (`MarkerPainter`) replicando a mesma estética e nós de seta.
6. Executar suíte de testes unitários e de integração com 100% de cobertura.
