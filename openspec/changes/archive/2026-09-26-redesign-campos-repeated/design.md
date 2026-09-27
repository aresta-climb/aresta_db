## Context

No editor de dados (`WidgetEditorDados`), coleções repetidas de mensagens e tipos primitivos são gerenciadas pelo componente `ContainerRepeatedWidget`. 
Atualmente:
- Para tipos escalares (`repeated string creditos`, `conquistadores`), o container empilha widgets `QLineEdit` de tamanho fixo juntamente com alça `⠿`, botões `▲`, `▼` e um botão retangular vermelho "Remover". Em resoluções médias e grandes, a falta de expansão adequada gera vazios desproporcionais entre esses controles.
- Para mapas, `WidgetCardMapa` é inserido na lista, mantendo no seu cabeçalho controles semelhantes (`▲`, `▼` e "Remover").
- Para mensagens genéricas, `WidgetColapsavel` abriga esses mesmos controles no seu cabeçalho.
- O botão de adicionar novos itens (`btn_add`) está posicionado no cabeçalho superior direito em todos os casos, e o cartão de subelementos (`_renderizar_cartao_subelementos`) no rodapé dos formulários também alinha a adição à direita.

## Goals / Non-Goals

**Goals:**
- Unificar o padrão estrutural de todas as coleções `repeated`: o botão de adição de item passa a ficar no **rodapé** da coleção (após os itens existentes ou no corpo do estado vazio).
- Padronizar a extrema direita de cada linha/cabeçalho de item exclusivamente para o botão de remoção em formato de ícone discreto (*ghost icon* com `fa5s.trash-alt`), eliminando os blocos vermelhos chamativos.
- Descontinuar os botões de subir (`▲`) e descer (`▼`), consolidando a reordenação unicamente através da alça de arraste (`⠿`) e do sistema de drag-and-drop já integrado ao histórico.
- Estruturar campos primitivos (como strings) em um cartão integrado fluido (com borda sutil, cantos arredondados e separadores), permitindo que os campos de texto expandam responsivamente com a largura da tela.
- Implementar fluxo de digitação contínua via tecla `Enter` nos campos escalares (adicionando um novo item e transferindo o foco automaticamente).
- Adaptar o cartão de subelementos (`_renderizar_cartao_subelementos`) para exibir o botão de ação no corpo inferior do cartão.
- Manter 100% de cobertura de testes unitários sem quebrar o histórico de Undo/Redo.

**Non-Goals:**
- Não altera comandos de histórico (`CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`), controladores nem modelos Protobuf.
- Não altera a renderização interna de campos filhos dentro de mensagens colapsáveis ou do editor de mapas.
- Não altera a árvore de navegação lateral (`WidgetEditorDadosArvore`).

## Decisions

### 1. Botão de Adição no Rodapé da Coleção
- **Decisão**: Mover `self.btn_add` do `header_layout` para um layout de rodapé posicionado logo abaixo de `self.items_layout`. Quando a coleção estiver vazia, exibir mensagem explicativa suave seguida do botão de adição.
- **Alternativas consideradas**:
  - *Manter botão no cabeçalho superior*: Rejeitado porque quebra o fluxo de leitura top-to-bottom, forçando o usuário a retornar os olhos e o mouse para o início da lista a cada item inserido.
  - *Botão flutuante*: Rejeitado por complexidade desnecessária em layouts Qt com rolagem.

### 2. Extrema Direita Exclusiva para Remoção com Ícone Discreto
- **Decisão**: Remover os botões `▲` e `▼` e substituir o botão "Remover" retangular vermelho por um botão de ícone compacto com a lixeira (`Icones.obter("lixeira")` ou `qta.icon('fa5s.trash-alt')`). O botão terá estilo neutro e transparente por padrão, adquirindo tom de alerta avermelhado suave apenas no estado `:hover`.
- **Alternativas consideradas**:
  - *Manter setas ao lado da lixeira*: Rejeitado para simplificar a interface e atender à diretriz direta do usuário de manter apenas o botão de remoção na lateral direita.
  - *Botão com texto 'Remover' menor*: Rejeitado porque a repetição do texto linha por linha continua poluindo a lista.

### 3. Container Integrado para Tipos Primitivos / Escalares
- **Decisão**: Envolver as linhas de itens primitivos em um `QFrame` com borda sutil (`#d0d7de`), cantos arredondados (`6px`) e fundo limpo. Cada item é inserido com separador horizontal e os campos de texto recebem política de expansão horizontal (`QSizePolicy.Policy.Expanding`), preenchendo o espaço disponível sem quebrar o alinhamento.
- **Alternativas consideradas**:
  - *Deixar os inputs soltos no formulário*: Rejeitado pois causa aspecto desorganizado e sensação de campos avulsos.

### 4. Atalho de Teclado `Enter` para Adição Rápida
- **Decisão**: Conectar o sinal `returnPressed` dos widgets `QLineEdit` de itens repetidos para disparar a adição do próximo item quando houver conteúdo digitado, aplicando imediatamente o foco (`setFocus()`) ao novo widget criado.
- **Alternativas consideradas**:
  - *Exigir atalho Ctrl+Enter*: Rejeitado pois `Enter` em campos de linha única é o comportamento esperado em listas e tags modernas (ex: Notion, Linear, Trello).

## Risks / Trade-offs

- **[Risco] Usuários que dependiam de cliques em setas para reordenar** → **Mitigação**: A alça visual `⠿` possui cursor de mão (`OpenHandCursor`), estilo visual claro e tooltip explicativa *"Arrastar para reordenar"*, além de indicador de linha azul durante o arraste.
- **[Risco] Testes unitários antigos que buscavam `btn_subir` e `btn_descer`** → **Mitigação**: Atualizar a suite de testes em `widget_editor_dados_test.py` e `widget_card_mapa_test.py` para validar a nova disposição dos botões no rodapé, o botão de lixeira e o atalho de teclado `Enter`.
