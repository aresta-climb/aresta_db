## Purpose

Define os padrões de empacotamento, integridade via checksum SHA-256, inclusão no manifesto de serving e disponibilização de documentos e anexos em croquis de escalada para consumo online e offline.

## Requirements

### Requirement: Empacotamento e Indexação de Anexos no Deploy
O pipeline de compilação de croquis (`deploy_generated.py`) DEVE (SHALL) inspecionar a existência do diretório `anexos/` na pasta do croqui, copiar seu conteúdo para a pasta gerada e indexar cada arquivo em `Croqui.arquivos_externos` com seu respectivo checksum SHA-256.

#### Scenario: Croqui com pasta de anexos contendo formulários
- **WHEN** o comando de deploy processa um croqui contendo arquivos na pasta `anexos/`
- **THEN** o sistema copia todos os arquivos para `generated/<croqui_id>/anexos/`
- **THEN** o sistema calcula o SHA-256 de cada anexo e os insere na lista `arquivos_externos` do `compilado.binarypb`

### Requirement: Inclusão Automática de Anexos no Manifesto Serving
O gerador do manifesto `arquivos_serving.yaml` DEVE (SHALL) incluir todos os arquivos externos declarados em `Croqui.arquivos_externos`, contemplando os arquivos da pasta `anexos/` com caminho relativo e checksum SHA-256.

#### Scenario: Geração do manifesto de distribuição
- **WHEN** o passo D do deploy gera o arquivo `generated/arquivos_serving.yaml`
- **THEN** o manifesto lista cada anexo sob o formato `- caminho_relativo: <croqui_id>/anexos/<arquivo>` com seu respectivo `checksum_sha256`

### Requirement: Cabeçalhos HTTP Apropriados no Serving
O script de sincronização com o armazenamento em nuvem (`serving/update_serving.py`) DEVE (SHALL) associar o cabeçalho `Content-Type` correto correspondente à extensão de cada arquivo ao realizar upload de anexos para o Cloudflare R2 / S3.

#### Scenario: Upload de arquivo PDF de anexo
- **WHEN** o `update_serving.py` realiza o envio de um arquivo com extensão `.pdf` para o armazenamento remoto
- **THEN** a requisição de upload define o metadado `ContentType` como `application/pdf`

### Requirement: Cálculo do Tamanho de Download com Anexos
A biblioteca de medição de tamanho (`calcular_tamanho_croqui_bytes`) DEVE (SHALL) computar o peso de todos os arquivos de anexos pertencentes ao croqui, incorporando-os ao valor total de `tamanho_download_bytes` exibido no índice.

#### Scenario: Cálculo do tamanho para croqui com anexos
- **WHEN** o tamanho do croqui é computado durante o deploy
- **THEN** os bytes dos arquivos contidos na pasta `anexos/` são somados ao tamanho do `compilado.binarypb` e das imagens
