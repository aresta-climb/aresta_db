## ADDED Requirements

### Requirement: Biblioteca de Processamento de Imagens de Campos
O sistema DEVE conter uma biblioteca pura em Python (`editor/core/processamento_imagem_campo.py`) responsável por inspecionar metadados de imagem (dimensões em pixels e tamanho em bytes/KB), sanitizar nomes de arquivos, verificar conflitos de arquivos existentes e converter/comprimir imagens em formato WebP.

#### Scenario: Leitura de metadados de imagem
- **WHEN** a biblioteca inspeciona um arquivo de imagem válido
- **THEN** retorna a tupla contendo largura, altura e tamanho formatado do arquivo

#### Scenario: Compressão e salvamento de imagem WebP
- **WHEN** a biblioteca processa um arquivo de imagem de entrada
- **THEN** gera um arquivo WebP comprimido com qualidade 85 e área redimensionada caso exceda 4 megapixels

#### Scenario: Sanitização de nome de arquivo
- **WHEN** a função recebe um nome de arquivo contendo espaços e caracteres especiais (ex: `Foto da Parede!.jpg`)
- **THEN** retorna o nome sanitizado em formato slug (ex: `foto_da_parede.webp`)

### Requirement: Pré-visualização e Metadados de Imagens na Interface
O sistema DEVE prover um componente de interface especializado (`WidgetCampoImagem`) para campos anotados com `CampoFormatoUi.IMAGEM` (ou com tipo MIME `image/*`), exibindo uma miniatura da imagem associada e seus metadados de arquivo.

#### Scenario: Campo com imagem válida existente
- **WHEN** o formulário carrega um campo com o caminho `imagens/thumbnail.webp` e o arquivo existe em disco
- **THEN** o widget exibe a miniatura da imagem com proporção preservada, o nome do arquivo, a resolução em pixels e o tamanho em KB

#### Scenario: Campo com imagem ausente ou vazio
- **WHEN** o campo está vazio ou o caminho indicado não existe no disco
- **THEN** o widget exibe um quadro com marcador visual informando que nenhuma imagem está selecionada ou que o arquivo não foi encontrado

### Requirement: Troca e Processamento Automático de Imagens
O sistema DEVE permitir ao usuário selecionar um arquivo de imagem local e realizar o processamento automático (conversão e compressão WebP) salvando o resultado na pasta `imagens/` do croqui e registrando a alteração no histórico.

#### Scenario: Troca de imagem com nome de arquivo fixo
- **WHEN** o usuário clica em "Trocar Imagem..." em um campo com `nome_arquivo_imagem = "thumbnail.webp"` e seleciona um arquivo `foto.jpg`
- **THEN** o sistema converte e comprime a imagem para WebP, salva o arquivo como `<croqui_database>/imagens/thumbnail.webp` e atualiza o valor do campo para `imagens/thumbnail.webp` via `CmdAlterarPrimitivo`

#### Scenario: Troca de imagem com nome personalizado
- **WHEN** o usuário seleciona um arquivo `minha_parede.png` em um campo sem nome fixo
- **THEN** o sistema abre um diálogo sugerindo o nome `minha_parede.webp` e permitindo personalização
- **AND WHEN** o usuário confirma
- **THEN** o arquivo é processado e salvo em `<croqui_database>/imagens/minha_parede.webp` e o campo atualizado via `CmdAlterarPrimitivo`

#### Scenario: Alerta de conflito de nome de imagem
- **WHEN** o usuário informa um nome de imagem que já existe na pasta `imagens/`
- **THEN** o diálogo exibe um aviso de que o arquivo já existe e solicita confirmação de sobrescrita

### Requirement: Integração com Editor de Imagens
O sistema DEVE permitir a transição direta do campo de imagem para o Editor de Imagens integrado.

#### Scenario: Abrir imagem no Editor de Imagens
- **WHEN** o usuário clica no botão "Abrir no Editor" em um campo de imagem válido
- **THEN** o sistema altera a visualização para a aba de Imagens e carrega a imagem correspondente na ferramenta de edição e recorte
