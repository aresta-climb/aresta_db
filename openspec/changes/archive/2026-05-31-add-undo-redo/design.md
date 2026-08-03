## Context

O Editor Aresta manipula um estado central (`Croqui` em Protobuf) através de três abas distintas: Dados (formulários dinâmicos baseados no proto), Imagens (sistema de arquivos) e Mapas (visões gráficas e markdown). Atualmente, a edição muta os dados diretamente. Não há suporte para Undo/Redo (Desfazer/Refazer). Widgets nativos do Qt (como `QLineEdit` e `QTextEdit`) possuem pilhas de histórico locais, mas elas são desconectadas da árvore de dados estruturados e falham em suportar operações estruturais (ex: deletar um nó).

## Goals / Non-Goals

**Goals:**
- Proteger o usuário de operações destrutivas acidentais (deleção de setor, troca de oneof, remoção de imagem).
- Fornecer uma linha do tempo única de Undo/Redo (Ctrl+Z / Ctrl+Shift+Z) consistente entre todas as abas.
- Preservar o foco e o estado do cursor ao máximo durante uma ação de Undo na edição de texto.

**Non-Goals:**
- Não visamos persistir a pilha de undo/redo em disco (fechar o app limpa o histórico).
- Não visamos reescrever o motor do `QTextEdit` do markdown, mas sim integrá-lo seletivamente ou desativar seu undo nativo em prol do global.

## Decisions

**1. Desativação do Undo Nativo (Abordagem Ditador Global)**
- *Decisão*: `QLineEdit` e `QSpinBox` terão o histórico local desativado. Mudanças emitirão comandos `QUndoCommand` globais.
- *Rationale*: Evita a "amnésia de foco", onde o histórico do widget é perdido quando o usuário clica em outro nó da árvore. Garante que Ctrl+Z sempre desfaça a última ação do *sistema*, e não apenas da caixa de texto atualmente focada.

**2. Comandos Protobuf Baseados em Introspecção**
- *Decisão*: Em vez de criar um comando para cada campo (`CmdMudarNome`, `CmdMudarAltitude`), criaremos comandos genéricos (`CmdAlterarPrimitivo`, `CmdRemoverRepeated`) que operam no nível de `Message` e `FieldDescriptor`.
- *Rationale*: Evita uma explosão combinatória de classes e adapta-se automaticamente caso o schema do Protobuf evolua.

**3. Merge de Comandos de Texto (`mergeWith`)**
- *Decisão*: Para evitar que a digitação de "Gato" crie 4 comandos separados de Undo, o comando de texto implementará `mergeWith` usando um hash baseado em `id(mensagem)` e `nome_do_campo`.
- *Rationale*: Desempenho e experiência do usuário (Undo apaga a palavra ou sequência de digitação, não letra por letra intermitentemente).

**4. Interceptação de Dragging via `mouseReleaseEvent`**
- *Decisão*: Nas abas de Mapas e Imagens, movimentos gráficos (`QGraphicsScene`) salvarão o estado inicial no `mousePressEvent` e emitirão o `QUndoCommand` apenas no `mouseReleaseEvent`.
- *Rationale*: Um evento `itemChange` contínuo geraria centenas de comandos por segundo. O evento de release consolida a ação de arrastar em um salto único de Undo.

## Risks / Trade-offs

- **[Risco] Perda de Foco da UI no Undo de Dados** → *Mitigação*: Implementar um mecanismo `AtualizadorUI` que descobre qual widget estava em foco antes do `load_node()` (ou da atualização) e tenta reaplicar o foco no widget correspondente recriado.
- **[Risco] Lixo no Sistema de Arquivos (Imagens, Markdown)** → *Mitigação*: Ao invés de usar `os.remove` ao deletar um arquivo (seja mapa ou imagem) via editor, o comando de remoção move o arquivo para uma pasta temporária secreta `.aresta_trash_interna`. O comando de Refazer deleta dessa lixeira, e o Desfazer restaura de lá.
