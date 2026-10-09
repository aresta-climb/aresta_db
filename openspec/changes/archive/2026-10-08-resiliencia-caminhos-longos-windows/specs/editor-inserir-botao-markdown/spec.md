# Spec Delta

## MODIFIED Requirements

### Requirement: Diálogo Modal de Inserção de Botão
Ao acionar o botão "Inserir Botão", o editor DEVE (SHALL) abrir o diálogo modal `DialogoInserirBotaoMarkdown`, permitindo configurar o texto do botão, selecionar um anexo local existente em `anexos/`, importar um novo arquivo do computador com sanitização e limite de 40 caracteres no tronco do nome, ou definir uma URL web externa.

#### Scenario: Inserção de anexo existente
- **WHEN** o usuário abre o diálogo, define o texto do botão como "Baixar Ficha (PDF)" e seleciona um arquivo PDF existente na pasta `anexos/`
- **THEN** o diálogo formata a tag Markdown correspondente `[Baixar Ficha (PDF)](anexos/ficha.pdf)`
- **THEN** ao confirmar, o texto é inserido na posição do cursor do editor

#### Scenario: Importação de novo arquivo do computador
- **WHEN** o usuário seleciona um arquivo externo ao croqui através do seletor ou solta um arquivo no diálogo
- **THEN** o sistema valida e sanitiza o nome do arquivo truncando o tronco em no máximo 40 caracteres, copia o arquivo para a pasta `anexos/` do croqui e gera o link Markdown correspondente
