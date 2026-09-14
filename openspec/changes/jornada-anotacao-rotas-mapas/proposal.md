## Why

Atualmente, anotar uma nova rota de escalada (especialmente boulders em fotos limpas da rocha) exige uma jornada fragmentada de cerca de 10 passos manuais distribuídos entre Editor de Dados, Editor de Imagens e Editor de Mapas. O usuário precisa criar o boulder nos dados, desenhar linhas separadas com um botão genérico de "Nova Linha / Escalada", atribuir IDs manuais em caixas de diálogo, criar uma referência relacional no painel lateral, buscar a entidade e linkar os POIs um a um.

Além disso, cenários de vias que compartilham início, fim ou travessias (como variantes e saídas compartilhadas) são extremamente complexos: exigem planejamento prévio e corte manual de múltiplos segmentos que não possuem integração "sticky" (nós soldados) entre si. Esta mudança unifica e automatiza essa jornada em um fluxo centrado no mapa com desenho contínuo, snap magnético ponto a ponto, fatiamento automático de linhas (em vértices ou no meio do traçado), aplicação inteligente da convenção semântica de marcação (estilo Ouroboulder) no escopo abrangente de todo o Setor, e substitui definitivamente o botão legado de "Nova Linha / Escalada".

A implementação segue estritamente os Princípios de Engenharia Aresta (`AGENTS.md`): abordagem Library-First com bibliotecas matemáticas e topológicas autônomas e desacopladas em `editor/core/`, 100% de cobertura de testes unitários, desenvolvimento orientado a testes (TDD Red-Green-Refactor), testes de integração prévios, simplicidade e modificações de estado exclusivamente via comandos na pilha de histórico (`QUndoCommand`).

## What Changes

- **Ação Rápida "+ Nova Rota" e Remoção do Botão Legado**: Substitui o antigo botão "Nova Linha / Escalada" (que exigia desenhar linhas desconectadas de entidades e vincular IDs manualmente) pelo novo botão de ação primária "+ Nova Rota" (com atalho `R`). Esse botão abre uma paleta limpa com busca de escaladas pré-existentes sem traçado no setor e opção de criar uma nova escalada (nome, tipo, grau) inline, entrando imediatamente no modo de desenho.
- **Desenho com Snap Magnético e Conexão Ponto a Ponto**: Permite desenhar o traçado na rocha clicando ponto a ponto, com snap magnético inteligente em nós e segmentos de outras linhas existentes.
- **Fatiamento Automático de Traçados ("Sticky")**: Quando um traçado conecta ou bifurca de uma linha existente (seja em um nó existente ou em qualquer ponto do meio da curva), a linha existente é fatiada automaticamente em subpartes reaproveitáveis, mantendo as referências originais intactas e sincronizadas.
- **Convenção Semântica Ouroboulder no Escopo do Setor**:
  - Inícios numerados sequencialmente considerando todos os mapas do setor (`1`, `2`, `3`...).
  - Se a mesma escalada já estiver traçada em outro mapa do mesmo setor (ex: foto de outro ângulo), o número identificador é reutilizado consistentemente.
  - Saídas compartilhadas rotuladas em conjunto (ex: `1, 2`).
  - Fins rotulados com letras (ex: `A`, `B`, `C`...).
  - Nós intermediários suportando símbolos geométricos (triângulo `▲`, estrela `★`, etc.).
  - IDs de POIs garantidos como disjuntos entre todos os mapas do mesmo setor para evitar qualquer colisão.
- **Desambiguação Inteligente de TOP sob Demanda**: Rotas isoladas terminam de forma limpa no topo da rocha sem círculos redundantes de TOP. Quando duas ou mais vias terminam em topos distintos após bifurcação ou convergem no mesmo topo, o editor gera automaticamente os círculos identificadores com letras de desambiguação para todas as vias envolvidas.
- **Integridade Atômica com Undo/Redo (Princípio VII de AGENTS.md)**: Todas as mutações decorrentes da criação de rota, fatiamento de linhas existentes, atualização de referências e nós são agrupadas em um único macro `QUndoCommand` na pilha `historico`.
- **Arquitetura Library-First (Princípio II de AGENTS.md)**: O cálculo de snap, projeção em spline, regras de rotulagem semântica, escopo de setor e fatiamento topológico de nós residem no módulo desacoplado `editor/core/topologia_trajeto.py`, 100% testável de forma isolada sem dependência de widgets Qt.

## Capabilities

### New Capabilities
- `desenho-rotas-mapas`: Define o fluxo de trabalho e a interface para vincular ou criar novas escaladas diretamente no Editor de Mapas, com snap magnético ponto a ponto, fatiamento topológico automático, remoção do botão legado de linha, numeração consistente no escopo do setor com IDs disjuntos e aplicação das convenções semânticas de início, fim e desambiguação de TOP.

### Modified Capabilities
- `tracados-vetoriais-mapas`: Atualiza os requisitos de interpolação e renderização para suportar concatenação contínua de subsegmentos fatiados pertencentes a uma mesma referência e manutenção da integridade de nós compartilhados coincidentes.

## Impact

- **Editor de Mapas (`editor/views/widget_editor_mapas.py`)**: Remoção do botão legado `btn_add_linha` e dos seus callbacks manuais; adição do botão "+ Nova Rota", atalho `R`, mira visual magnética de snap e integração do desenho ponto a ponto.
- **Biblioteca de Topologia (`editor/core/topologia_trajeto.py`)**: Nova biblioteca independente para snap magnético, projeção em curva, fatiamento de nós, resolução de identificadores no escopo do setor e convenção semântica.
- **Diálogo de Seleção/Criação (`editor/views/dialogos/dialogo_nova_rota_mapa.py`)**: Nova paleta modal enxuta para busca de rotas existentes e criação inline.
- **Controlador de Mapas (`editor/controllers/mapas_controller.py`)**: Novo método `adicionar_rota_com_tracado` orquestrando mutações via `QUndoCommand` com macro atômico.
