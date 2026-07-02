## Why

Clicar no botão de salvar trava toda a interface do usuário (UI), degradando a experiência do usuário. Adicionalmente, o botão de adicionar ajuste de câmera no editor de mapas não funciona corretamente, pois a câmera não aparece na cena quando ativada. Por fim, durante o modo de linkagem, POIs podem ser acidentalmente arrastados ao tentar selecioná-los. Estes três problemas serão corrigidos adotando uma abordagem orientada a testes (TDD) com o objetivo de alcançar 100% de cobertura de testes unitários nas áreas afetadas.

## What Changes

- O processo de salvamento (em `area_principal.py`) será refatorado para executar de forma assíncrona usando uma thread de background (`QThread`/`Worker`), evitando o bloqueio do Event Loop do PyQt6.
- A interface de usuário irá apresentar um estado de "salvando" para notificar o usuário e evitar ações simultâneas indesejadas.
- A função `iniciar_modo_camera` (em `widget_editor_mapas.py`) e a criação do `ItemCameraOverlay` serão corrigidos para garantir que o retângulo de ajuste seja sempre exibido na cena com as dimensões e o Z-Value corretos.
- Durante o modo de linkagem de POIs, a propriedade de movimentação dos itens de POI na cena será temporariamente desabilitada para evitar cliques acidentais que desloquem o ponto em vez de apenas selecioná-lo.
- Serão escritos e atualizados testes automatizados garantindo 100% de coverage para essas funcionalidades.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `salvamento-assincrono`: O salvamento passa a ser executado em background sem travar a interface.
- `ajuste-camera`: Restabelecida a correta visualização do overlay de ajuste de câmera no editor de mapas.
- `poi-bloqueio-linkagem`: Previne arrasto acidental de POIs enquanto o modo de linkagem estiver ativo.

## Impact

- **Código afetado**: `editor/legacy_views/area_principal.py`, `editor/views/widget_editor_mapas.py`.
- **Testes afetados**: `editor/legacy_views/area_principal_test.py`, `editor/views/widget_editor_mapas_test.py`.
- **UI**: A interface não irá mais congelar ao salvar, o overlay roxo da câmera voltará a ficar visível ao clicar em seu respectivo botão de adição, e POIs não se moverão caso o usuário clique e arraste acidentalmente durante a linkagem.
