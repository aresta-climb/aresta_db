## Context

Atualmente, `ContainerRepeatedWidget` em `editor/views/widget_editor_dados.py` delega a renderização de sub-mensagens repetidas ao `WidgetColapsavel`. Para mensagens com `mensagem_formato_na_ui = MAPA` (a mensagem `Mapa`), os campos internos são manipulados exclusivamente pela ferramenta visual de mapas (`WidgetEditorMapas`), de modo que o accordion colapsável abriga unicamente o botão *"Abrir no Editor de Mapas"*. Como `Mapa` não possui campos de texto como `nome` ou `titulo`, o accordion exibia apenas o rótulo genérico `▶ Mapas [i]`, gerando uma interface estática, sem pré-visualização das fotos das paredes e sem feedback visual de mudança de posição durante a reordenação.

## Goals / Non-Goals

**Goals:**
- Criar o componente independente `WidgetCardMapa` em `editor/views/componentes/widget_card_mapa.py` (Princípio II - Library-First) com 100% de cobertura de testes unitários.
- Renderizar `WidgetCardMapa` diretamente em `ContainerRepeatedWidget` para campos de mapas, sem accordion ou toggles de expansão.
- Exibir miniatura da foto do mapa com proporção mantida, resolução (`largura × altura px`), caminho do arquivo e o botão de navegação para o Editor de Mapas.
- Integrar com a alça de arraste (`AlcaArrasteItem`), botões `▲`/`▼` e botão `Remover`, mantendo histórico atômico via `CroquiController` e `QUndoStack` (Princípio VII).
- Reagir ao sinal `model.imagem_alterada` e à reordenação dinâmica da lista (`model.repeated_movido`).

**Non-Goals:**
- Editar anotações vetoriais, referências ou pontos de interesse dentro do card de dados (essas edições continuam sob responsabilidade do `WidgetEditorMapas`).
- Alterar o comportamento de outros campos repetidos que ainda necessitam de formulários expansíveis (como `escaladas`).

## Decisions

### Decisão 1: Criação de `WidgetCardMapa` como Biblioteca Independente
- **Abordagem**: Criar um componente `QFrame` modular em `editor/views/componentes/widget_card_mapa.py`, com API clara (`definir_indice()`, `atualizar_dados()`, sinais de solicitação de arraste e navegação).
- **Alternativas consideradas**:
  - *Modificar `WidgetColapsavel` para suportar modo não-colapsável e miniatura*: Rejeitado por violar a coesão (adiciona lógica específica de mapas a um componente genérico de accordion).
  - *Construir o card diretamente com layouts soltos no `ContainerRepeatedWidget`*: Rejeitado por inflar o container e dificultar testes unitários isolados com 100% de cobertura.

### Decisão 2: Layout do Card (Cabeçalho de Controle + Corpo com Miniatura)
- **Abordagem**:
  - Linha superior (Cabeçalho): `AlcaArrasteItem` (`⠿`), rótulo `Mapa [i] - <nome_arquivo>`, botões `▲`, `▼` e `Remover`.
  - Linha inferior (Corpo): Miniatura à esquerda (`QLabel` com tamanho fixo de área `160×100 px`, fundo neutro e imagem redimensionada com `KeepAspectRatio`), e painel de informações à direita (caminho, dimensões e botão destacado `Abrir no Editor de Mapas`).
- **Alternativas consideradas**:
  - *Miniatura minúscula apenas no cabeçalho*: Não ofereceria visibilidade suficiente para diferenciar ângulos ou setores semelhantes.
  - *Card vertical com imagem em largura total*: Ocuparia espaço vertical excessivo no formulário, dificultando a visualização de múltiplos mapas do mesmo setor.

### Decisão 3: Carregamento de Imagem via `CroquiModel`
- **Abordagem**: Obter bytes da imagem via `model.obter_bytes_imagem(caminho_imagem_mapa)`. Isso garante suporte imediato e consistente a imagens em buffer de memória RAM e imagens gravadas em disco, sem acoplamento a diretórios físicos. Se a imagem não for encontrada, exibir um placeholder suave com texto *"Sem Imagem"*.
- **Alternativas consideradas**:
  - *Ler diretamente de `QPixmap(caminho_disco)`*: Falharia para imagens recém-adicionadas em memória que ainda não foram gravadas no disco ao salvar o croqui.

## Risks / Trade-offs

- **[Risco] Mapa sem dimensões ou sem imagem carregada** → **Mitigação**: O componente trata graciosamente caminhos vazios, imagens ausentes e dimensões zero, exibindo rótulos informativos de placeholder sem emitir exceções.
- **[Risco] Atualização de índices após reordenação** → **Mitigação**: `ContainerRepeatedWidget._atualizar_indices_e_botoes()` é estendido para chamar `card.definir_indice(idx)` e atualizar os botões nos cards de mapa, exatamente como faz com `WidgetColapsavel`.
