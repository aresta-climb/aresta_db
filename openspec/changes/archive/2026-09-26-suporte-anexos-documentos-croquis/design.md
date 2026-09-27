## Context

Veja `proposal.md` para a motivação. 
O ecossistema Aresta distribui dados estruturados compilados em `.binarypb` acompanhados de arquivos externos distribuídos via Cloudflare R2 / CDN HTTP em `https://serving.arestaclimb.com/vX/`.
No pipeline atual (`deploy_generated.py`), apenas a pasta `imagens/` e extensões `.webp` são tratadas como `arquivos_externos`. O aplicativo móvel (`aresta_app`) possui infraestrutura madura de cache atômico e sincronização por isolados (`SyncIsolate`) que já itera cegamente sobre qualquer arquivo declarado em `Croqui.arquivos_externos`, porém o ecossistema ainda não previa a inclusão de documentos anexos (PDFs, termos, fichas de cadastro).

## Goals / Non-Goals

**Goals:**
- Permitir que croquis incluam documentos anexos (como PDFs de autorização e termos de risco) em uma pasta dedicada `anexos/`.
- Indexar automaticamente os anexos em `Croqui.arquivos_externos` com SHA-256 e incluí-los no manifesto `arquivos_serving.yaml`.
- Configurar o upload no `serving/update_serving.py` com o cabeçalho `Content-Type: application/pdf`.
- Fornecer ferramenta no Editor Desktop para inserção de botões/links de anexos com suporte a cópia de arquivos e Undo/Redo.
- Implementar o `ProvedorAnexoAresta` no `aresta_app` com cache em 3 camadas e abertura nativa via `open_filex`.

**Non-Goals:**
- Não criar um visualizador de PDF proprietário dentro do Flutter (usaremos o visualizador padrão do sistema operacional do usuário).
- Não criar novas entidades complexas no Protobuf para botões (usar a sintaxe Markdown padrão `[Texto](anexos/arquivo.pdf)`).
- Não alterar a estrutura de dados existente de vias, setores ou mapas.

## Decisions

### Decisão 1: Links Nativos em Markdown (Opção A) vs Novo Campo Protobuf
- **Decisão**: Usar links no padrão Markdown `[Rótulo do Botão](anexos/documento.pdf)` e ensiná-los ao `OfflineMarkdown` para renderização como botão de destaque.
- **Alternativas consideradas**:
  - *Adicionar `DocumentoAnexo` em `DestinoBotao`*: Poluiria a lista de botões principais do pico com formulários que precisam do contexto textual das regras para serem compreendidos.
  - *Novo campo em `ArquivoMarkdown`*: Criaria complexidade no Protobuf sem ganho expressivo sobre o próprio texto.
- **Justificativa**: Segue o princípio de **Simplicidade e Anti-Abstração**. O autor tem total liberdade de posicionar os botões no meio do texto instrutivo.

### Decisão 2: Pasta `anexos/` e Reuso de `Croqui.arquivos_externos`
- **Decisão**: Armazenar os arquivos na pasta `anexos/` do croqui e mapeá-los para `Croqui.arquivos_externos`.
- **Alternativas consideradas**:
  - *Criar um campo `anexos_externos` separado*: Desnecessário, pois `ArquivoExterno(caminho, checksum_sha256)` já é completamente genérico.
- **Justificativa**: O motor de sincronização offline (`SyncIsolate`) do `aresta_app` já baixa automaticamente qualquer arquivo listado em `arquivosExternos`. Assim, os anexos tornam-se offline automaticamente com zero modificações no isolado de download.

### Decisão 3: Integração ao `arquivos_serving.yaml` e Content-Type no R2
- **Decisão**: Garantir que o passo D do `deploy_generated.py` inclua os anexos no manifesto e que `serving/update_serving.py` associe `application/pdf` aos arquivos `.pdf`.
- **Justificativa**: Sem o cabeçalho correto no S3/R2, visualizadores nativos e navegadores podem falhar ao tentar abrir ou baixar o arquivo via streaming online.

### Decisão 4: `open_filex` e Resolução em 3 Camadas no `aresta_app`
- **Decisão**: Criar `ProvedorAnexoAresta` espelhando a arquitetura de `ProvedorImagemAresta`:
  1. Armazenamento Permanente (`downloads/<id>/anexos/...`)
  2. Cache Volátil (`temp_cache/<id>/anexos/...<hash>`)
  3. Streaming CDN (`https://serving.arestaclimb.com/...`) com gravação atômica `.tmp` -> `rename` e validação SHA-256.
  E abrir via `OpenFilex.open()`.
- **Alternativas consideradas**:
  - *`url_launcher`*: Falha em dispositivos Android modernos ao tentar abrir arquivos locais com `file://` devido à falta de `FileProvider`.
- **Justificativa**: O `open_filex` abstrai o `FileProvider` (Android) e `QuickLook` (iOS), garantindo compatibilidade total com os leitores instalados no celular.

### Decisão 5: `DialogoInserirBotaoMarkdown` com `CmdInserirBotaoMarkdown` no Editor
- **Decisão**: Implementar o diálogo modal permitindo arrastar/selecionar arquivos e empacotar a alteração em um comando `QUndoCommand`.
- **Justificativa**: Cumpre o **Princípio VII (Edições de Estado via Comandos do Histórico)**, garantindo que adicionar um botão e seu anexo seja 100% reversível via Undo/Redo.

## Risks / Trade-offs

- **[Risco] Dispositivo sem aplicativo compatível para ler PDF instalado**
  → *Mitigação*: O `open_filex` retorna status (`ResultType.noAppToOpen`). Caso isso ocorra, o app pode apresentar um diálogo amigável sugerindo a instalação de um leitor de PDF.
- **[Risco] Anexos muito pesados aumentando o tempo de sincronização**
  → *Mitigação*: Os PDFs do CEMONTA extraídos têm menos de 200 KB cada. O `calcular_tamanho_croqui_bytes` exibe o tamanho real do download antes de o usuário confirmar.
- **[Risco] Mutações no disco sem sincronização com a RAM do Editor**
  → *Mitigação*: O comando `CmdInserirBotaoMarkdown` gerencia tanto o texto no editor quanto a cópia dos bytes do arquivo no `CroquiModel`, permitindo salvar e desfazer de forma limpa.

## Migration Plan

1. **Retrocompatibilidade**: Croquis sem a pasta `anexos/` continuam gerando o `compilado.binarypb` e `arquivos_serving.yaml` exatamente como antes.
2. **Rollback**: Caso seja necessário reverter, a remoção da pasta `anexos/` ou dos links correspondentes retorna o croqui ao estado anterior sem quebrar esquemas de banco de dados.
