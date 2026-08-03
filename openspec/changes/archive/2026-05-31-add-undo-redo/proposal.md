## Why

Atualmente, qualquer modificação feita pelo usuário na interface gráfica do Editor Aresta muta diretamente a estrutura de dados (`Croqui` em Protobuf). Isso impede que ações sejam revertidas (o famoso `Ctrl+Z`), resultando em uma péssima experiência de usuário onde um erro acidental (como deletar um setor inteiro) causa perda irreversível de trabalho. Precisamos de um esquema de Undo/Redo robusto e global para proteger os usuários contra erros de operação e melhorar o fluxo de edição de dados e de gráficos simultaneamente.

## What Changes

- Desativação do Undo/Redo nativo das caixas de texto (`QLineEdit`, `QTextEdit`) para evitar conflito com a linha do tempo principal (Abordagem "Ditador Global").
- Introdução de uma pilha de histórico global (`QUndoStack` único) pertencente à `JanelaPrincipal` que sincroniza as ações cronológicas de todas as abas.
- Criação de Comandos de Histórico (padrão `QUndoCommand`) granulares e baseados em introspecção de Protobuf para a edição de dados.
- Implementação de fusão de comandos (`mergeWith`) para suportar digitação de texto sem criar milhares de instâncias de "Desfazer".
- Suporte a comandos de Undo/Redo nas operações de Gráficos (Mapas e Imagens), interceptando as ações na soltura do mouse (`mouseReleaseEvent`).
- Atualização do documento `PRINCIPIOS.md` para incluir o princípio de desenvolvimento: toda e qualquer modificação no croqui pelo editor deve ser feita através de comandos integrados ao histórico, nunca mutando propriedades diretamente.
- Recuperação inteligente do foco do formulário reconstruído ao aplicar Undo/Redo na árvore de Dados.

## Capabilities

### New Capabilities
- `undo-redo-global`: Gerenciamento da pilha de histórico global, fusão de comandos textuais, interface com `QUndoGroup/QUndoStack` e gerenciamento seguro da "Lixeira Interna" para arquivos genéricos (markdown, imagens).
- `undo-redo-protobuf`: Geração de Comandos dinâmicos (`QUndoCommand`) para operações baseadas em modificações de `Message` e `FieldDescriptor`.
- `undo-redo-graficos`: Comandos específicos para lidar com transformações no `QGraphicsScene` (arrasto, bounding boxes).

### Modified Capabilities
- Nenhuma, pois a funcionalidade base de editar o Croqui se mantém, apenas encapsulada no padrão Command.

## Impact

- **UI (Visões)**: Quase todos os widgets reativos em `widget_editor_dados.py`, `editor_mapas.py` e `widget_editor_imagens.py` serão impactados. Precisarão despachar Comandos para a pilha em vez de invocar `setattr()` nativo ou deletar arquivos fisicamente de imediato.
- **Testes**: De acordo com os `PRINCIPIOS.md`, novos testes unitários profundos para a validação da fusão de comandos (`mergeWith`) do Protobuf e do rollback state serão necessários. Testes de integração deverão cobrir a interface do usuário acionando Ctrl+Z via Qt Test.
- **Simplicidade**: A introspecção do Protobuf na criação de comandos genéricos mantém a abstração pragmática e simples, sem precisarmos de dezenas de Comandos repetitivos. O uso da infraestrutura nativa do Qt (`QUndoStack`) evita reinventar a roda.
