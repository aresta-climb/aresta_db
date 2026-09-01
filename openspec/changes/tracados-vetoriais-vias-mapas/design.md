# Design Técnico: Sistema de Traçados Vetoriais e Destaque Dinâmico de Vias em Mapas

## Context

O Aresta DB gerencia mapas e fotos de setores de escalada, armazenando pontos de interesse e referências em arquivos Markdown com Frontmatter YAML e compilando-os para Protobuf (.pb) para consumo offline no aplicativo móvel. Historicamente, os croquis eram derivados de digitalizações de PDFs legados onde as linhas das vias já estavam impressas nas imagens como mapas de bits (raster). Nesses casos, o sistema utilizava apenas caixas delimitadoras (`circulo`, `quadrado`, `retangulo`, `poligono`) para identificar a área de clique em volta de números.

Com a criação de novos croquis fotografados diretamente na rocha (fotos limpas de alta definição), surgiu a necessidade de:
1. Desenhar trajetos vetoriais contínuos de vias e boulders.
2. Definir tipos semânticos em português para cada nó do traçado (base/início, passagens de curva, proteções fixas, paradas intermediárias, cruxes e tops).
3. Suportar o compartilhamento de trechos em comum entre vias e variantes como um grafo semântico conectado através de `Referencia.ids`.
4. Otimizar a entrega para o aplicativo móvel com pré-compilação em SVG Path (`caminho_svg`) para renderização 100% acelerada por GPU (Impeller/Skia) e consumo de bateria próximo de zero.

Este documento segue rigorosamente os sete princípios de engenharia definidos em `PRINCIPIOS.md` (Tudo em Português, Library-First, 100% de Cobertura de Testes, TDD, Testes de Integração em Primeiro Lugar, Simplicidade e Anti-Abstração, e Edições de Estado via Comandos do Histórico).

## Goals / Non-Goals

**Goals:**
- Estender o Protobuf (`croqui.proto`) com a mensagem `LinhaTrajeto`, estruturada com `oneof representacao { DadosConteudoLinha conteudo; DadosCompiladosLinha compilado; }` com todos os identificadores em português brasileiro.
- Criar biblioteca isolada e pura (Library-First) em `editor/core/spline_catmull_rom.py` (sem dependências de GUI como PyQt) para converter nós de controle em Curvas de Bézier Cúbicas (formato padrão SVG Path `caminho_svg`), com 100% de cobertura de testes unitários.
- Implementar a ferramenta interativa de Caneta de Traçado no Editor de Mapas (`WidgetEditorMapas`), permitindo criação de linhas, movimentação de nós com suavização em tempo real a 60 FPS, menu de contexto de tipos de nós, e suporte integral a histórico `QUndoCommand`.
- Integrar a compilação offline no pipeline de build (`build.py` / `scripts/deploy_generated.py`) para calcular automaticamente os caminhos SVG e caixas delimitadoras nos arquivos compilados.
- Garantir total retrocompatibilidade com todos os croquis existentes no banco de dados.

**Non-Goals:**
- Não substituir ou quebrar as geometrias de POI existentes (`circulo`, `quadrado`, `retangulo`, `poligono`), que continuam funcionando normalmente para croquis legados.
- Não implementar roteamento automático ou detecção de rocha por visão computacional neste momento (os nós são inseridos manualmente pelo autor do croqui).

## Decisions

### Decisão 1: Separação de Representação (`conteudo` vs `compilado`) no Protobuf
- **Escolha:** Usar `oneof representacao` dentro de `LinhaTrajeto`, onde `conteudo` guarda a lista de nós semânticos (`repeated NoTrajeto nos = 1;`) e `compilado` guarda o `caminho_svg`, `caixa_delimitadora` e marcadores gerados pelo compilador.
- **Justificativa:** O repositório git e o frontmatter YAML mantêm apenas os dados editáveis e legíveis por humanos (`conteudo`), enquanto o arquivo binário distribuído para o aplicativo contém o caminho SVG pronto para o motor gráfico (`compilado`), eliminando processamento desnecessário no celular.
- **Nomenclatura (Princípio I):** Todos os campos e enums são em português (`caminho_svg`, `caixa_delimitadora`, `rotulo`, `INICIO_BASE`, `INICIO_AGACHADO`, `PROTECAO_FIXA`, `TOP_PARADA`, `CRUX`).
- **Alternativas consideradas:**
  - *Calcular Catmull-Rom em tempo real no app:* Rejeitado por consumir bateria e exigir duplicação da lógica matemática complexa em Dart e Python.
  - *Salvar apenas SVG Path cru no YAML:* Rejeitado porque caminhos SVG crus não preservam a semântica dos nós (chapeletas, cruxes, tipo de saída) nem facilitam a edição posterior no editor desktop.

### Decisão 2: Algoritmo Centripetal Catmull-Rom para Interpolação de Curvas (Library-First)
- **Escolha:** Utilizar a formulação Centripetal ($\alpha = 0.5$) da Spline Catmull-Rom para converter os nós em Curvas de Bézier Cúbicas em um módulo isolado e puro `editor/core/spline_catmull_rom.py`.
- **Justificativa:** Atende ao Princípio II (Library-First). O módulo é autossuficiente, puramente matemático, sem dependência do PyQt, podendo ser utilizado tanto pelas views do editor quanto pelos scripts de compilação CLI (`build.py`). A curva passa **estritamente por todos os pontos definidos pelo usuário**, com curvatura $C^1$ suave, sem criar quinas duras e sem oscilações/laços indesejados (*cusps*).
- **Alternativas consideradas:**
  - *Bézier Cúbica com alças manuais (estilo Pen Tool do Illustrator):* Rejeitado por ser muito complexo e demorado para usuários que não são designers gráficos.
  - *Polilinha reta (segmentos lineares):* Rejeitado por produzir traçados com visual quebrado e pouco profissional em paredes de rocha.

### Decisão 3: Composição de Trechos via `Referencia.ids` (Simplicidade & Anti-Abstração)
- **Escolha:** Tratar cada trecho de linha como um `ElementoVisual` com ID próprio no mapa e compor vias e variantes associando múltiplos IDs na `Referencia` (`ids: ["trecho_comum", "trecho_variante"]`).
- **Justificativa:** Modela naturalmente a realidade das falésias onde dezenas de vias compartilham as primeiras costuras ou saídas. Evita duplicar geometria e permite que o app faça o highlight completo da linha composta dinamicamente, seguindo o Princípio VI (Simplicidade).

### Decisão 4: Mutações de Nós Mediadas Estritamente por `QUndoCommand`
- **Escolha:** Todo movimento de nó, alteração de tipo de nó, adição ou remoção de ponto na linha deve ser executado através de comandos na pilha global `QUndoStack` no `MapasController`.
- **Justificativa:** Atende rigorosamente ao Princípio VII da engenharia do Aresta, assegurando consistência de estado e capacidade de desfazer/refazer em qualquer momento da edição gráfica, sem mutações diretas em manipuladores de eventos da UI.

## Risks / Trade-offs

- **[Risco: Vias com nós muito próximos gerando descontinuidades na spline]** → *Mitigação:* A biblioteca `spline_catmull_rom.py` normaliza a distância entre nós consecutivos e descarta nós duplicados colidentes ($dist < 1px$) com cobertura de testes unitários dedicada.
- **[Risco: Conexão visual imperfeita entre dois trechos compartilhados]** → *Mitigação:* Implementação de recurso de *snapping* magnético no editor para que o início de um trecho variante conecte exatamente nas coordenadas do nó da bifurcação.
- **[Risco: Incompatibilidade com os 400+ croquis legados]** → *Mitigação:* `LinhaTrajeto` é adicionada como um novo campo oneof sem alterar os índices ou semânticas de `circulo`, `quadrado`, `retangulo` e `poligono`.

## Migration Plan

1. Atualizar a definição em `aresta_api/proto/croqui.proto` e compilar os protos com `build.py protos`.
2. Implementar e testar unitariamente `editor/core/spline_catmull_rom.py` via TDD rigoroso (100% coverage).
3. Expandir `editor/core/geometrias_poi.py` e os conversores do editor para suportar `linha`.
4. Implementar a ferramenta de desenho e o item gráfico `ItemTrajetoLinha` no `widget_editor_mapas.py` com integração a `QUndoCommand`.
5. Atualizar os scripts de compilação (`scripts/deploy_generated.py`) para pré-calcular o `caminho_svg` para o payload compilado.
6. Executar todos os testes de integração e unitários com `build.py test` e `build.py coverage`.

## Open Questions

Nenhuma questão em aberto pendente. O modelo de dados, nomes de campos em português (`conteudo` vs `compilado`, `caminho_svg`, `caixa_delimitadora`) e arquitetura de composição foram alinhados.
