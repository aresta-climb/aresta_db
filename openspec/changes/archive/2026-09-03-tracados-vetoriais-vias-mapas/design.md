# Design Técnico: Sistema de Traçados Vetoriais, Cores e Destaque Dinâmico de Vias em Mapas

## Context

O Aresta DB gerencia mapas e fotos de setores de escalada, armazenando pontos de interesse e referências em arquivos Markdown com Frontmatter YAML e compilando-os para Protobuf (.pb) para consumo offline no aplicativo móvel. Historicamente, os croquis eram derivados de digitalizações de PDFs legados onde as linhas das vias já estavam impressas nas imagens como mapas de bits (raster). Nesses casos, o sistema utilizava apenas caixas delimitadoras (`circulo`, `quadrado`, `retangulo`, `poligono`) para identificar a área de clique em volta de números.

Com a criação de novos croquis fotografados diretamente na rocha (fotos limpas de alta definição), surgiu a necessidade de:
1. Desenhar trajetos vetoriais contínuos de vias e boulders.
2. Atribuir cores personalizadas (`cor`) a cada elemento visual e traçado, permitindo diferenciar vias vizinhas e destacar linhas com cores de alto contraste sobre diferentes tipos de rocha (granito, calcário, arenito).
3. Definir tipos semânticos em português para cada nó do traçado (base/início, passagens de curva, proteções fixas, paradas intermediárias, cruxes e tops).
4. Suportar o compartilhamento de trechos em comum entre vias e variantes como um grafo semântico conectado através de `Referencia.ids`.
5. Otimizar a entrega para o aplicativo móvel com pré-compilação em SVG Path (`caminho_svg`) para renderização 100% acelerada por GPU (Impeller/Skia) e consumo de bateria próximo de zero.

Este documento segue rigorosamente os sete princípios de engenharia definidos em `PRINCIPIOS.md` (Tudo em Português, Library-First, 100% de Cobertura de Testes, TDD, Testes de Integração em Primeiro Lugar, Simplicidade e Anti-Abstração, e Edições de Estado via Comandos do Histórico).

## Goals / Non-Goals

**Goals:**
- Estender o Protobuf (`croqui.proto`) com o campo `cor` (hex `#RRGGBB`) em `PontoDeInteresse` e a mensagem `LinhaTrajeto`, estruturada com `oneof representacao { DadosConteudoLinha conteudo; DadosCompiladosLinha compilado; }` com todos os identificadores em português brasileiro.
- Disponibilizar uma paleta padrão de cores de escalada otimizada para alto contraste em fotos de rocha:
  - Vermelho (`#FF1744`): Vias exigentes, projetos, destaque.
  - Laranja (`#FF6D00`): Alto contraste em calcário cinza e granito escuro.
  - Amarelo (`#FFD600`): Clássica para boulders e topos solares.
  - Verde Lima (`#00E676`): Vias fáceis/moderadas e acessos.
  - Ciano (`#00E5FF`): Linhas técnicas e vias esportivas.
  - Roxo (`#D500F9`): Vias móveis, mistas e variantes.
  - Branco (`#FFFFFF`): Traçado neutro de alto contraste.
  - Cinza (`#757575`): Projetos em conquista.
- Criar biblioteca isolada e pura (Library-First) em `editor/core/spline_catmull_rom.py` (sem dependências de GUI como PyQt) para converter nós de controle em Curvas de Bézier Cúbicas (formato padrão SVG Path `caminho_svg`), com 100% de cobertura de testes unitários.
- Implementar a ferramenta interativa de Caneta de Traçado e seletor de cores no Editor de Mapas (`WidgetEditorMapas`), com suporte integral a histórico `QUndoCommand`.
- Integrar a compilação offline no pipeline de build (`build.py` / `scripts/deploy_generated.py`) para calcular automaticamente os caminhos SVG e caixas delimitadoras nos arquivos compilados.
- Garantir total retrocompatibilidade com todos os croquis existentes no banco de dados.

**Non-Goals:**
- Não substituir ou quebrar as geometrias de POI existentes (`circulo`, `quadrado`, `retangulo`, `poligono`), que continuam funcionando normalmente e agora também podem receber o campo `cor`.
- Não implementar roteamento automático ou detecção de rocha por visão computacional neste momento (os nós são inseridos manualmente pelo autor do croqui).

## Decisions

### Decisão 1: Campo `cor` Universal em `PontoDeInteresse`
- **Escolha:** Adicionar `string cor = 10;` no nível de `PontoDeInteresse`.
- **Justificativa:** Permite que qualquer elemento do mapa (linhas de via, áreas de polígono, círculos de número, caixas) receba uma cor personalizada. Se não fornecido, o editor e o app utilizam a cor padrão do sistema (verde para POIs genéricos, laranja/ciano para linhas de escalada).
- **Formato:** Hexadecimal `#RRGGBB` (ex: `"#FF6D00"`), compatível universalmente com Qt, Flutter, CSS e YAML.

### Decisão 2: Separação de Representação (`conteudo` vs `compilado`) no Protobuf
- **Escolha:** Usar `oneof representacao` dentro de `LinhaTrajeto`, onde `conteudo` guarda a lista de nós semânticos (`repeated NoTrajeto nos = 1;`) e `compilado` guarda o `caminho_svg`, `caixa_delimitadora` e marcadores gerados pelo compilador.
- **Justificativa:** O repositório git e o frontmatter YAML mantêm apenas os dados editáveis e legíveis por humanos (`conteudo`), enquanto o arquivo binário distribuído para o aplicativo contém o caminho SVG pronto para o motor gráfico (`compilado`), eliminando processamento desnecessário no celular.

### Decisão 3: Algoritmo Centripetal Catmull-Rom para Interpolação de Curvas (Library-First)
- **Escolha:** Utilizar a formulação Centripetal ($\alpha = 0.5$) da Spline Catmull-Rom para converter os nós em Curvas de Bézier Cúbicas em um módulo isolado e puro `editor/core/spline_catmull_rom.py`.
- **Justificativa:** Atende ao Princípio II (Library-First). O módulo é autossuficiente, puramente matemático, sem dependência do PyQt, podendo ser utilizado tanto pelas views do editor quanto pelos scripts de compilação CLI (`build.py`). A curva passa **estritamente por todos os pontos definidos pelo usuário**, com curvatura $C^1$ suave, sem criar quinas duras e sem oscilações/laços indesejados (*cusps*).

### Decisão 4: Composição de Trechos via `Referencia.ids` (Simplicidade & Anti-Abstração)
- **Escolha:** Tratar cada trecho de linha como um `ElementoVisual` com ID próprio no mapa e compor vias e variantes associando múltiplos IDs na `Referencia` (`ids: ["trecho_comum", "trecho_variante"]`).
- **Justificativa:** Modela naturalmente a realidade das falésias onde dezenas de vias compartilham as primeiras costuras ou saídas. Evita duplicar geometria e permite que o app faça o highlight completo da linha composta dinamicamente, seguindo o Princípio VI (Simplicidade).

### Decisão 5: Mutações de Nós e Cores Mediadas Estritamente por `QUndoCommand`
- **Escolha:** Todo movimento de nó, alteração de tipo de nó, mudança de cor, adição ou remoção de ponto na linha deve ser executado através de comandos na pilha global `QUndoStack` no `MapasController`.
- **Justificativa:** Atende rigorosamente ao Princípio VII da engenharia do Aresta, assegurando consistência de estado e capacidade de desfazer/refazer em qualquer momento da edição gráfica, sem mutações diretas em manipuladores de eventos da UI.

## Risks / Trade-offs

- **[Risco: Vias com nós muito próximos gerando descontinuidades na spline]** → *Mitigação:* A biblioteca `spline_catmull_rom.py` normaliza a distância entre nós consecutivos e descarta nós duplicados colidentes ($dist < 1px$) com cobertura de testes unitários dedicada.
- **[Risco: Cores com baixo contraste em determinadas fotos]** → *Mitigação:* A paleta recomendada no editor prioriza cores fluorescentes/vibrantes com alto contraste tonal contra calcário, granito e arenito.
- **[Risco: Incompatibilidade com os 400+ croquis legados]** → *Mitigação:* `LinhaTrajeto` e `cor` são opcionais, preservando compatibilidade com todos os croquis existentes.

## Migration Plan

1. Atualizar a definição em `aresta_api/proto/croqui.proto` com `LinhaTrajeto` e campo `cor`, compilando os protos com `build.py protos`.
2. Implementar e testar unitariamente `editor/core/spline_catmull_rom.py` via TDD rigoroso (100% coverage).
3. Expandir `editor/core/geometrias_poi.py` e os conversores do editor para suportar `cor` e `linha`.
4. Implementar a ferramenta de desenho, o item gráfico `ItemTrajetoLinha` e o seletor de cores no `widget_editor_mapas.py` com integração a `QUndoCommand`.
5. Atualizar os scripts de compilação (`scripts/deploy_generated.py`) para pré-calcular o `caminho_svg` para o payload compilado.
6. Executar todos os testes de integração e unitários com `build.py test` e `build.py coverage`.

## Open Questions

Nenhuma questão em aberto pendente. O modelo de dados, nomes de campos em português (`conteudo` vs `compilado`, `cor`, `caminho_svg`, `caixa_delimitadora`) e paleta de cores foram alinhados.
