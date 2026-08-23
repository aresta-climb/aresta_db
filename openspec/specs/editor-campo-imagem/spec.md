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
O modelo `CroquiModel` DEVE manter em memória RAM os bytes de imagens novas ou substituídas (`_imagens_em_memoria`), permitindo leitura de miniaturas e controle de histórico sem escrever no disco até o salvamento.

#### Scenario: Armazenamento em memória sem escrita em disco
- **WHEN** uma nova imagem é associada a um campo via `CmdAlterarCampoImagem`
- **THEN** os bytes da imagem são armazenados em `_imagens_em_memoria` no modelo e nenhum arquivo é criado no disco

#### Scenario: Desfazer substituição de imagem (Undo)
- **WHEN** o usuário executa Undo após substituir uma imagem
- **THEN** o modelo restaura a referência anterior e a pré-visualização volta a exibir a imagem original sem alterar arquivos em disco

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
O sistema DEVE permitir ao usuário selecionar um arquivo de imagem local e realizar o processamento em memória, atualizando o campo via comando de histórico.

#### Scenario: Troca de imagem com nome de arquivo fixo
- **WHEN** o usuário clica em "Trocar Imagem..." em um campo com `nome_arquivo_imagem = "thumbnail.webp"` e seleciona um arquivo `foto.jpg`
- **THEN** o sistema comprime a imagem para bytes WebP, registra no modelo e atualiza o campo via `CmdAlterarCampoImagem`

#### Scenario: Troca de imagem com nome personalizado
- **WHEN** o usuário seleciona um arquivo `minha_parede.png` em um campo sem nome fixo
- **THEN** o sistema abre um diálogo sugerindo o nome `minha_parede.webp` e permitindo personalização
- **AND WHEN** o usuário confirma
- **THEN** a imagem é processada para a RAM e o campo é atualizado via `CmdAlterarCampoImagem`

#### Scenario: Alerta de conflito de nome de imagem
- **WHEN** o usuário informa um nome de imagem que já existe na pasta `imagens/` ou na memória
- **THEN** o diálogo exibe um aviso de que o arquivo já existe e solicita confirmação de substituição no momento de salvar

### Requirement: Integração e Sincronização com Editores de Imagens e Mapas
O sistema DEVE permitir a transição direta para o Editor de Imagens e sincronizar as abas de Imagens e Mapas após o salvamento.

#### Scenario: Abrir imagem no Editor de Imagens
- **WHEN** o usuário clica no botão "Abrir no Editor" em um campo de imagem válido
- **THEN** o sistema altera a visualização para a aba de Imagens e carrega a imagem correspondente na ferramenta de edição e recorte

#### Scenario: Recarregamento de Imagens e Mapas após salvar
- **WHEN** o salvamento do croqui é concluído com sucesso
- **THEN** a `PaginaImagens` e a `PaginaMapas` recarregam suas listas de imagens a partir do disco atualizado

