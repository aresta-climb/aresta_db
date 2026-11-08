## MODIFIED Requirements

### Requirement: Buffer de Imagens em Memória no Modelo
O modelo `CroquiModel` SHALL manter em memória RAM os bytes de imagens novas ou substituídas (`_imagens_em_memoria`), permitindo leitura de miniaturas e controle de histórico exclusivamente via comandos canônicos (`CmdAlterarImagem` e `CmdAlterarCampo` agrupados em `CmdMacro`) sem mutação direta pela View e sem escrever no disco até o salvamento.

#### Scenario: Armazenamento em memória sem escrita em disco
- **WHEN** uma nova imagem é confirmada para um campo no `WidgetCampoImagem`
- **THEN** a View emite o sinal com o caminho e os bytes processados sem mutar diretamente `CroquiModel`, e o `CroquiController` empilha `CmdMacro` (`CmdAlterarImagem` + `CmdAlterarCampo`) armazenando os bytes em `_imagens_em_memoria` e preservando `bytes_antigos` para reversão

#### Scenario: Desfazer substituição de imagem (Undo)
- **WHEN** o usuário executa `Undo` após substituir uma imagem em um campo com nome fixo (ex: `imagens/thumbnail.webp`) ou nome livre
- **THEN** o comando restaura os `bytes_antigos` no buffer `_imagens_em_memoria` e o caminho anterior no Protobuf, e a pré-visualização volta imediatamente a exibir a imagem original

#### Scenario: Gravação física atômica no salvamento
- **WHEN** a ação de salvar croqui (`salvar_croqui`) é executada
- **THEN** todas as imagens pendentes em `_imagens_em_memoria` são gravadas fisicamente no diretório `database/<croqui>/imagens/`

### Requirement: Troca de Imagens com Validação de Nomes
O sistema SHALL permitir ao usuário trocar ou selecionar a imagem de um campo (`WidgetCampoImagem`) utilizando o wizard unificado de duas abas (`"Importar Nova Imagem"` com Drag & Drop, preview, recorte interativo e metadados ricos, e `"Imagens do Croqui"` com galeria de imagens em RAM e disco), aplicando o orçamento de resolução contextual e atualizando o campo via comando de histórico.

#### Scenario: Troca de imagem com nome de arquivo fixo
- **WHEN** o usuário clica em `"Trocar Imagem..."` em um campo com `nome_arquivo_imagem = "thumbnail.webp"`
- **THEN** o sistema abre o wizard unificado em modo de destino fixo (`thumbnail.webp`) permitindo importar e recortar uma nova imagem ou escolher da galeria do croqui e, ao confirmar, atualiza os bytes WebP e o campo via `CroquiController.alterar_campo_imagem`

#### Scenario: Troca de imagem com nome personalizado
- **WHEN** o usuário clica em `"Trocar Imagem..."` em um campo sem nome fixo (ex: `caminho_imagem_capa`)
- **THEN** o sistema abre o wizard unificado permitindo importar uma nova imagem com sugestão e edição de nome `.webp` ou selecionar uma imagem existente na aba `"Imagens do Croqui"`, atualizando o campo via `CroquiController.alterar_campo_imagem`

#### Scenario: Alerta de conflito de nome de imagem
- **WHEN** o usuário informa na aba `"Importar Nova Imagem"` (em modo de nome livre) um nome de arquivo que já existe na pasta `imagens/` ou na memória RAM
- **THEN** o wizard exibe um alerta de conflito em tempo real e bloqueia a confirmação até que um nome único seja informado ou que a imagem existente seja escolhida pela aba `"Imagens do Croqui"`
