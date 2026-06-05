## Contexto

Atualmente, o `scripts/editar_mapas.py` é um aplicativo PyQt6 completo que gerencia sua própria janela, carregamento de arquivos e lógica de edição. Para integrá-lo ao Aresta Editor, precisamos desacoplar a lógica de interface (Widgets/GraphicsItems) da lógica de aplicação (MainWindow) e da lógica de dados (manipulação de YAML).

## Objetivos / Não-Objetivos

**Objetivos:**
- Extrair a funcionalidade de edição de mapas em um Widget reutilizável.
- Integrar este Widget na página "Mapas" da Janela Principal.
- Garantir que o Widget funcione com o croqui carregado na sessão principal.
- Manter o script original funcional como um wrapper em volta do novo Widget.
- Garantir que `scripts/editar_mapas_test.py` continue passando com o mínimo de alterações possível.
- Seguir o princípio Library-First, movendo lógica de processamento para uma biblioteca.

**Não-Objetivos:**
- Reescrever totalmente o motor de renderização (GraphicsScene/View).
- Adicionar novas funcionalidades de edição de mapas além das já existentes (Círculo, Box, Área Livre).

## Decisões

### 1. Refatoração em Camadas (Library-First)
- **Camada de Dados (`editor/core/mapas.py`)**: Conterá a lógica de manipulação dos dados dos mapas (conversão de tipos de POI, carregamento/salvamento de YAML específico de mapas).
- **Camada de Visão (`editor/views/editor_mapas.py`)**: Conterá os `GraphicsItems` (POI), a `GraphicsScene` e o `WidgetEditorMapas`.
- **Integração (`editor/views/area_principal.py`)**: A `PaginaMapas` instanciará o `WidgetEditorMapas`.

### 2. Gerenciamento de Estado e Salvamento
- O `WidgetEditorMapas` será responsável por gerenciar as edições visuais e atualizar o estado interno (YAML).
- O salvamento continuará sendo disparado pelo botão "Salvar" dentro do widget ou integrado ao botão "Salvar" global do editor (preferencialmente ambos para manter compatibilidade).

### 3. Compatibilidade com Script Independente
- O `scripts/editar_mapas.py` será simplificado para apenas instanciar uma `QMainWindow` que contém o `WidgetEditorMapas`, mantendo a mesma interface de linha de comando.
- Os nomes `logic_convert_box_to_circle` e `DrawingScene` devem permanecer disponíveis (ou ser importados) em `editar_mapas.py` para não quebrar os testes existentes.

## Riscos / Desafios

- **Dependência de Caminhos**: O script original assume uma estrutura de pastas específica. A biblioteca deve ser flexível o suficiente para receber o caminho base do croqui.
  - *Mitigação*: Passar o `Path` do croqui para o construtor do Widget.
- **Conflito de PyQt6**: Garantir que não haja múltiplas instâncias de `QApplication` se o widget for testado isoladamente.
  - *Mitigação*: Seguir padrões de inicialização de widgets PyQt.
