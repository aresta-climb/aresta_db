## Why

Editar as referências de um mapa no formato YAML é propenso a erros de digitação e causa uma grande desconexão visual, pois o nome da referência não é facilmente associável às formas desenhadas no mapa. Além disso, ajustar a câmera padrão (zoom e posição) de forma manual é muito difícil sem um feedback visual (*WYSIWYG*).
Permitir a edição das Referências dentro do próprio Editor de Mapas aumenta a consistência, garante que os dados estejam sempre 100% válidos via busca no CroquiModel, e melhora absurdamente a experiência do usuário.

## What Changes

- Adição de um Painel de Referências no lado direito do Editor de Mapas.
- Um modal de busca em todo o CroquiModel (buscando por Grupo, Setor, Via/Boulder) para iniciar uma nova referência.
- Modo de cursor "Linkagem", permitindo selecionar interativamente quais `ids` (círculos/retângulos) no mapa pertencem a uma Referência.
- Interação "Hover" no Painel Direito que destaca imediatamente as formas lincadas no mapa.
- Adição da funcionalidade de definir `ajuste_de_camera` de forma visual: um overlay no mapa limitando a proporção da tela (ex: 9:16), para que o usuário ajuste o zoom/foco visualmente, com "corte/sombra" visual de 20% no topo e base para indicar a zona segura de visão.

## Capabilities

### New Capabilities
- `editor-mapas-referencias`: Funcionalidade completa do painel direito, modo de linkagem e ajuste de câmera visual.

### Modified Capabilities
- `editor-mapas`: Modificação para acomodar o novo layout de 3 colunas (Painel esquerdo, ViewCentral, Painel direito) e novos callbacks de interação do mouse quando em modo linkagem.

## Impact

- `MapasController`: Adição de comandos (`CmdAdicionarRepeated`, etc.) direcionados à propriedade `referencias`.
- `WidgetEditorMapas`: Adição do Painel direito, modal de busca e lógica para o overlay do ajuste de câmera.
- Sem impacto no `.proto` já que o schema atual para `Referencia` e `AjusteDeCamera` já acomoda o que foi planejado.
