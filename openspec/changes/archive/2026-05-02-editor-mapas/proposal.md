## Why

Atualmente, a edição de pontos de interesse em mapas é realizada através de um script independente (`scripts/editar_mapas.py`). Integrar esta funcionalidade diretamente na janela principal do Aresta Editor proporciona uma experiência de usuário mais fluida e profissional, eliminando a necessidade de alternar entre diferentes janelas ou scripts para realizar tarefas comuns de edição de croquis.

## What Changes

- **Integração do Editor de Mapas**: A página "Mapas" (acessível pelo botão correspondente na barra lateral) deixará de ser um placeholder e passará a exibir o editor de mapas integrado.
- **Refatoração do script `editar_mapas.py`**: O script será refatorado para expor sua lógica central como um widget reaproveitável, permitindo sua incorporação na interface principal do editor.
- **Carregamento Automático**: O editor de mapas será inicializado automaticamente com os dados do croqui que está sendo editado no momento.
- **Manutenção da Independência**: O script `scripts/editar_mapas.py` continuará funcionando como uma ferramenta independente para uso via linha de comando.
- **Conformidade com Princípios**: Toda a implementação seguirá os princípios de "Tudo em Português", "Library-First" e TDD.

## Capabilities

### New Capabilities
- `editor-mapas`: Capacidade de editar pontos de interesse em mapas (círculos, caixas e áreas livres) diretamente dentro da interface principal do editor.

### Modified Capabilities
- `editor-area-principal`: A visão de "Mapas" deixará de ser um mock e passará a integrar o widget do editor de mapas.

## Impact

- `editor/views/area_principal.py`: Atualização da `PaginaMapas` para instanciar e exibir o widget de edição de mapas.
- `scripts/editar_mapas.py`: Refatoração para separar a lógica da interface em um widget (possivelmente movendo partes para uma biblioteca em `editor/core/`).
- `editor/core/`: Possível criação de uma nova biblioteca `editor_mapas_lib.py` seguindo o princípio Library-First.
