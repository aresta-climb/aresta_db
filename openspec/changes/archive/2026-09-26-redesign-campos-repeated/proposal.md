## Why

A interface gráfica de coleções repetidas (`repeated` fields do Protobuf) no formulário do editor de dados (`WidgetEditorDados`) apresenta sérios problemas de usabilidade, alinhamento visual e ergonomia:
1. **Dispersão e Desalinhamento**: O botão de "Adicionar Item" fica isolado no canto superior direito do cabeçalho, fora do fluxo de leitura natural de cima para baixo. Em itens escalares (como `creditos` e `conquistadores`), a largura fixa do campo de texto somada à ausência de políticas expansivas faz com que botões de reordenação (`▲`, `▼`) flutuem em pleno espaço vazio, distantes do texto ao qual pertencem.
2. **Poluição Visual Excessiva**: Cada linha exibe um botão de remoção vermelho largo e chamativo (`#d9534f`), criando uma "parede de alertas vermelhos" que compete visualmente com os dados cadastrados.
3. **Múltiplos Controles Conflitantes**: Botões de subir/descer na direita poluem a linha e tornam a interface confusa, mesmo quando a alça de arraste (`⠿`) para drag-and-drop já está disponível.
4. **Falta de Fluidez na Digitação**: O usuário precisa recorrer repetidamente ao mouse para adicionar cada novo item de texto simples, sem atalho de teclado (`Enter`).

Este redesign unifica o comportamento e o visual de todas as coleções repetidas (escalares, mapas e sub-mensagens colapsáveis), movendo a adição para o rodapé da lista, reservando a extrema direita exclusivamente para o botão de remoção em formato de ícone discreto, e transformando listas escalares em cartões integrados e fluidos.

## What Changes

- **Botão de Adição no Rodapé**: Em todas as listas `repeated` (`ContainerRepeatedWidget`, `WidgetCardMapa`, `WidgetColapsavel`), o botão de adicionar item é transferido do canto superior direito do cabeçalho para o rodapé da respectiva coleção/container, alinhando-se ao fluxo de leitura vertical.
- **Linha Limpa com Remoção Exclusiva à Direita**: Remoção dos botões de subir (`▲`) e descer (`▼`) da interface; a reordenação passa a ser guiada exclusivamente pela alça visual de arrastar e soltar (`⠿`). A extrema direita de cada linha passa a abrigar unicamente o botão de remoção.
- **Botão de Remoção Discreto (*Ghost Icon*)**: O botão vermelho retangular largo com o texto "Remover" é substituído por um botão de ícone de lixeira sutil (`fa5s.trash-alt`), em tom neutro/cinza por padrão e com destaque de alerta suave apenas no *hover*.
- **Container Integrado para Tipos Escalares**: Campos repetidos de tipos primitivos (como strings de créditos e conquistadores) passam a ser agrupados em um cartão integrado (tabela leve com borda sutil, cantos arredondados e divisores suaves), onde os campos de texto expandem para ocupar o espaço disponível responsivamente.
- **Adição Rápida via Tecla Enter**: Ao pressionar `Enter` em um campo de texto escalar preenchido, um novo item é criado automaticamente no modelo/histórico e o foco de digitação é transferido para o novo campo imediatamente.
- **Harmonização do Cartão de Subelementos**: O rodapé de subelementos da árvore (`_renderizar_cartao_subelementos`, ex: "Escaladas", "Setores") é atualizado para exibir o botão de ação rápida no corpo inferior do cartão em vez de comprimido à direita.

## Capabilities

### New Capabilities

*(Nenhuma nova capacidade introduzida; a mudança refina o comportamento de formulários existentes).*

### Modified Capabilities

- `editor-dados-formularios`: Atualiza os requisitos visuais e funcionais de coleções repetidas no formulário, movendo a ação de adição para o rodapé, padronizando a extrema direita exclusivamente para remoção discreta por ícone, consolidando a reordenação via alça de arrastar e soltar, adicionando criação por `Enter` e estruturando campos escalares em cartões integrados.

## Impact

- **Código Afetado**:
  - `editor/views/widget_editor_dados.py`: refatoração de `ContainerRepeatedWidget`, `WidgetColapsavel` e `_renderizar_cartao_subelementos`.
  - `editor/views/componentes/widget_card_mapa.py`: simplificação do cabeçalho do card de mapa (remoção de `btn_subir`/`btn_descer` e padronização do botão de exclusão).
  - `editor/views/estilo.py`: verificação ou registro do ícone de lixeira (`fa5s.trash-alt`) para uso padronizado.
- **Testes Afetados**:
  - `editor/views/widget_editor_dados_test.py` e `editor/views/componentes/widget_card_mapa_test.py`: atualização de testes que validavam cliques em `btn_subir`/`btn_descer` para validar a alça de arraste e os novos botões/posições de adição e remoção.
- **Compatibilidade e Modelos**: Não afeta o esquema Protobuf nem o histórico de Undo/Redo (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`), apenas a camada de apresentação (`View`).
