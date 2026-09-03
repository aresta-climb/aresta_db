## Context

O editor de texto Markdown do Editor Aresta (`WidgetEditorMarkdown`), empregado na edição de notas, capas e descrições de setores e picos, vinha apresentando uma latência severa durante a digitação ativa (travamentos de centenas de milissegundos a múltiplos segundos para digitar poucas palavras).

A investigação detalhada revelou que o problema decorre de uma reação em cadeia síncrona no loop de eventos principal do Qt a cada pressionamento de tecla:
1. Conexão direta de `QTextEdit.textChanged` sem qualquer temporizador de coalescência;
2. Renderização dupla do documento Markdown e redimensionamento completo de imagens (`scale_images`) a cada tecla, devido ao ciclo de eco através de `set_conteudo`;
3. Sincronização síncrona do diário em disco com truncamento de arquivo e destruição do cache de telemetria em comandos mesclados (`pode_mesclar=True`), forçando releituras do disco e compressões WebP repetidas via Pillow;
4. Reconstrução indevida da lista de mapas no `WidgetEditorMapas` ao escutar sinais genéricos de `dado_alterado` para campos textuais;
5. Acúmulo descontrolado de instâncias de `GlobalUndoRedoFilter` no widget através de chamadas repetidas a `installEventFilter`.

Para sanar essas falhas respeitando integralmente os **Princípios de Engenharia Aresta** (`PRINCIPIOS.md`), o design estabelece uma abordagem modular (*Library-First*), orientada a testes (*TDD*), com testes de integração em primeiro lugar, comandos no histórico (*Undo/Redo*) e nomenclatura 100% em português brasileiro.

## Goals / Non-Goals

**Goals:**
- **Princípio I (Tudo em Português)**: Toda a arquitetura, classes, métodos e testes devem ser nomeados estritamente em português brasileiro.
- **Princípio II (Library-First)**: Criar a biblioteca independente `editor/core/temporizador_coalescencia.py` para isolar toda a lógica de temporização, adiamento e descarga forçada de eventos.
- **Princípio V (Testes de Integração em Primeiro Lugar)**: Estabelecer testes de integração cobrindo o fluxo completo de digitação, undo/redo e sincronização antes da implementação detalhada.
- **Princípio VII (Comandos do Histórico)**: Garantir que a consolidação adiada emita comandos `CmdAlterarPrimitivo` preservando a integridade da pilha de `QUndoStack` e a recuperação contra encerramento anômalo.
- Eliminar o ciclo de eco em `set_conteudo` quando o texto recebido for idêntico ao já existente no campo de edição.
- Eliminar a invalidação do cache de telemetria durante a coalescência de comandos contínuos no `GerenciadorDiario`.
- Bloquear a reconstrução da lista de mapas da cidade diante de alterações em campos textuais.
- Garantir instalação idempotente de `GlobalUndoRedoFilter`.

**Non-Goals:**
- Não alterar os formatos de arquivo serializados no diário (`pickle`) ou o esquema Protobuf do croqui.
- Não reescrever o parser de Markdown nativo do Qt (`QTextBrowser.setMarkdown`) nem adotar motores externos de navegação.

## Decisions

### Decisão 1: Biblioteca Autônoma `TemporizadorCoalescencia` (Princípio II - Library-First)
- **Localização**: `editor/core/temporizador_coalescencia.py` com testes em `editor/core/temporizador_coalescencia_test.py`.
- **Contrato**:
  - `agendar(callback: Callable[[], None]) -> None`: Inicia ou reinicia o temporizador com atraso padrão de 250ms.
  - `descartar() -> None`: Cancela execuções pendentes sem disparar o callback.
  - `forcar_descarga() -> None`: Se houver um callback pendente agendado, executa-o imediatamente e cancela o temporizador.
  - `esta_ativo() -> bool`: Retorna se há uma ação pendente aguardando a expiração do tempo.
- **Racional**: Evita poluir o componente gráfico de 2.700 linhas com gerenciamento direto de timers Qt, permitindo testar toda a lógica de temporização e cancelamento em isolamento unitário estrito.
- **Alternativas consideradas**:
  - *Usar `QTimer` direto embutido na classe da view*: Rejeitado por violar o Princípio II (Library-First) e dificultar testes unitários desacoplados.

### Decisão 2: Guarda de Igualdade em `set_conteudo` para Quebra de Ciclo de Eco
- **Abordagem**: Em `WidgetEditorMarkdown.set_conteudo(novo_valor)`, comparar imediatamente a string recebida com `self.editor.toPlainText()`. Se forem idênticas, a função retorna imediatamente (`return`).
- **Racional**: Quando o editor dispara a consolidação no modelo, o modelo emite `dado_alterado`, que por sua vez invoca `set_conteudo`. Com a guarda, a segunda chamada a `preview.setMarkdown()` e `scale_images()` é sumariamente ignorada.

### Decisão 3: Atualização Incremental no `GerenciadorDiario` e Preservação de Cache
- **Abordagem**: Criar no `GerenciadorDiario` o método `atualizar_ultimo_comando_pendente(comando)`, que:
  1. Atualiza o último registro do cache `_comandos_anonimizados_cache` em memória RAM, sem zerá-lo.
  2. Atualiza o diário pendente em disco apenas regravando os comandos da pilha de forma eficiente sem truncamento total destrutivo.
- **Racional**: Evita que comandos mesclados pelo `QUndoStack` forcem `diario.descartar_pendente()`, o que destruía o cache de telemetria e forçava a re-leitura de todos os arquivos de diário e re-compressão de fotos pelo Pillow a cada caractere digitado.

### Decisão 4: Filtragem Estrita em `WidgetEditorMapas._atualizar_lista_mapas`
- **Abordagem**: Modificar a guarda inicial de `_atualizar_lista_mapas` para ignorar alterações onde o campo pertença a campos textuais (`conteudo`, `descricao`, `notas`, `nome`, etc.).
- **Racional**: Evita que a lista inteira de mapas de todos os picos e setores seja apagada e reconstruída na GUI durante a digitação de textos.

### Decisão 5: Instalação Idempotente de `GlobalUndoRedoFilter`
- **Abordagem**: Proteger a chamada de `installEventFilter` com a propriedade `_undo_filter_instalado` no widget.
- **Racional**: Evita empilhar centenas de instâncias do mesmo filtro no objeto Qt ao longo da sessão, preservando a velocidade do teclado.

## Risks / Trade-offs

- **[Risco] Perda de texto se o usuário fechar a janela ou salvar antes do temporizador expirar**
  - *Mitigação*: `EditorTextoMarkdown.focusOutEvent` e o método `forcar_consolidacao()` do `WidgetEditorMarkdown` invocam `self.temporizador.forcar_descarga()`, garantindo que qualquer digitação pendente seja enviada ao modelo antes de qualquer outra ação.
- **[Risco] Concorrência entre digitação rápida e chamadas externas de `set_conteudo`**
  - *Mitigação*: Se `set_conteudo` receber um texto genuinamente diferente (ex.: resultado de um `Undo` externo acionado por atalho global), qualquer temporização pendente é descartada e o novo texto externo assume o controle.
