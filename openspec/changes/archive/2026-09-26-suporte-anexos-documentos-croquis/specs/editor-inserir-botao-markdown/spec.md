## Purpose

Define o comportamento da interface de edição de Markdown para permitir a inserção intuitiva de botões de ação e documentos anexos através de diálogo modal dedicado e comandos com histórico de Undo/Redo.

## ADDED Requirements

### Requirement: Botão de Ação na Barra de Ferramentas de Markdown
O componente `WidgetEditorMarkdown` DEVE (SHALL) disponibilizar um botão de ação "Inserir Botão" em seu cabeçalho, posicionado ao lado do botão de inserção de imagem.

#### Scenario: Visualização do editor de Markdown
- **WHEN** o usuário seleciona um campo de texto formatado como Markdown no formulário de edição
- **THEN** o cabeçalho exibe o botão "Inserir Botão" com estilo consistente com as demais ações da barra de ferramentas

### Requirement: Diálogo Modal de Inserção de Botão
Ao acionar o botão "Inserir Botão", o editor DEVE (SHALL) abrir o diálogo modal `DialogoInserirBotaoMarkdown`, permitindo configurar o texto do botão, selecionar um anexo local existente em `anexos/`, importar um novo arquivo do computador ou definir uma URL web externa.

#### Scenario: Inserção de anexo existente
- **WHEN** o usuário abre o diálogo, define o texto do botão como "Baixar Ficha (PDF)" e seleciona um arquivo PDF existente na pasta `anexos/`
- **THEN** o diálogo formata a tag Markdown correspondente `[Baixar Ficha (PDF)](anexos/ficha.pdf)`
- **THEN** ao confirmar, o texto é inserido na posição do cursor do editor

#### Scenario: Importação de novo arquivo do computador
- **WHEN** o usuário seleciona um arquivo externo ao croqui através do seletor ou solta um arquivo no diálogo
- **THEN** o sistema valida o nome do arquivo, copia o arquivo para a pasta `anexos/` do croqui e gera o link Markdown correspondente

### Requirement: Gestão Transacional de Botões com Histórico Undo e Redo
A inserção do botão e a inclusão de arquivos anexos importados DEVEM (SHALL) ser despachadas através de comando transacional na pilha de histórico (`QUndoCommand`), assegurando reversibilidade completa.

#### Scenario: Desfazer e refazer inserção de botão
- **WHEN** o usuário insere um botão com um anexo novo e em seguida executa a ação Desfazer (Ctrl+Z)
- **THEN** o texto do botão é removido do editor e a adição do arquivo anexo é revertida no estado de rascunho
- **WHEN** o usuário executa a ação Refazer (Ctrl+Y)
- **THEN** o texto e o arquivo anexo são restaurados no estado do croqui
