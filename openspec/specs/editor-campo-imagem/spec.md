# editor-campo-imagem Specification

## Purpose
TBD - created by archiving change novos-campo-formato-ui. Update Purpose after archive.
## Requirements
### Requirement: Biblioteca de Processamento de Imagens de Campos
O sistema DEVE conter uma biblioteca pura em Python (`editor/core/processamento_imagem_campo.py`) responsável por inspecionar metadados de imagem a partir de bytes ou caminhos (dimensões em pixels e tamanho em bytes/KB), sanitizar nomes de arquivos, verificar conflitos de arquivos e converter/comprimir imagens em formato WebP retornando bytes em RAM.

#### Scenario: Leitura de metadados de imagem a partir de bytes
- **WHEN** a biblioteca recebe bytes de uma imagem válida
- **THEN** retorna a largura, altura e tamanho formatado do arquivo

#### Scenario: Compressão de imagem para bytes WebP em memória
- **WHEN** a biblioteca processa um arquivo de imagem de entrada
- **THEN** retorna os bytes da imagem comprimida em formato WebP com qualidade 85 e área redimensionada caso exceda 4 megapixels

#### Scenario: Sanitização de nome de arquivo
- **WHEN** a função recebe um nome de arquivo contendo espaços e caracteres especiais (ex: `Foto da Parede!.jpg`)
- **THEN** retorna o nome sanitizado em formato slug (ex: `foto_da_parede.webp`)

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

### Requirement: Pré-visualização e Metadados de Imagens na Interface
O sistema DEVE prover um componente de interface especializado (`WidgetCampoImagem`) para campos anotados com `CampoFormatoUi.IMAGEM` (ou com tipo MIME `image/*`), exibindo uma miniatura da imagem associada (obtida da memória RAM ou do disco) e seus metadados de arquivo.

#### Scenario: Campo com imagem válida existente
- **WHEN** o formulário carrega um campo com o caminho `imagens/thumbnail.webp` e a imagem existe em RAM ou disco
- **THEN** o widget exibe a miniatura da imagem com proporção preservada, o nome do arquivo, a resolução em pixels e o tamanho em KB

#### Scenario: Campo com imagem ausente ou vazio
- **WHEN** o campo está vazio ou o caminho indicado não existe na RAM nem no disco
- **THEN** o widget exibe um quadro com marcador visual informando que nenhuma imagem está selecionada ou que o arquivo não foi encontrado

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

### Requirement: Integração e Sincronização com Editores de Imagens e Mapas
O sistema DEVE permitir a transição direta para o Editor de Imagens e sincronizar as abas de Imagens e Mapas após o salvamento.

#### Scenario: Abrir imagem no Editor de Imagens
- **WHEN** o usuário clica no botão "Abrir no Editor" em um campo de imagem válido
- **THEN** o sistema altera a visualização para a aba de Imagens e carrega a imagem correspondente na ferramenta de edição e recorte

#### Scenario: Recarregamento de Imagens e Mapas após salvar
- **WHEN** o salvamento do croqui é concluído com sucesso
- **THEN** a `PaginaImagens` e a `PaginaMapas` recarregam suas listas de imagens a partir do disco atualizado

### Requirement: Orçamento de Imagem de 1 Megapixel para Capas
O sistema SHALL suportar a aplicação do limite de resolução de 1.000.000 pixels (`AREA_MAXIMA_ESCALADA` / 1 MP) na compressão WebP em memória ao inserir ou trocar fotos através do campo de capa (`caminho_imagem_capa`).

#### Scenario: Inserção de foto de capa de alta resolução
- **WHEN** o usuário seleciona uma imagem de 12 megapixels (ex: 4000x3000 px) no campo de foto de capa de um Setor ou Grupo
- **THEN** o sistema redimensiona a imagem para que a área total não exceda 1.000.000 pixels, preservando a proporção original e comprimindo em WebP Q85 na memória RAM

### Requirement: Exibição Priorizada de Capa no Topo do Formulário
O sistema SHALL renderizar o campo `caminho_imagem_capa` no topo absoluto do formulário de dados de entidades `Setor` e `Grupo`, posicionado antes do campo `nome`.

#### Scenario: Renderização de formulário de Setor com capa
- **WHEN** o formulário de visualização/edição de um `Setor` é exibido na interface do usuário
- **THEN** o widget de imagem associado ao campo `caminho_imagem_capa` é posicionado como primeiro elemento da área principal do formulário, acima do campo de texto `nome`

#### Scenario: Renderização de formulário de Grupo com capa
- **WHEN** o formulário de visualização/edição de um `Grupo` é exibido na interface do usuário
- **THEN** o widget de imagem associado ao campo `caminho_imagem_capa` é posicionado como primeiro elemento da área principal do formulário, acima do campo de texto `nome`

