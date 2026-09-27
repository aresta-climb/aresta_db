# Proposta: Suporte a Anexos e Documentos em Croquis

## Why

Diversas áreas de escalada (como o Campo Escola de Montanhismo - CEMONTA na Serra do Lenheiro, gerido pelo Exército Brasileiro, e unidades de conservação com controle de acesso) exigem o preenchimento prévio e envio de termos de reconhecimento de risco, formulários de acesso e cadastros de brigada para autorizar a entrada de escaladores. Atualmente, o croqui de São João Del Rei referencia esses arquivos apenas através de um link externo para uma pasta no Google Drive, o que inviabiliza o acesso offline nas montanhas, expõe o sistema a links quebrados de terceiros e não fornece uma experiência nativa de abertura e compartilhamento de formulários no aplicativo móvel (`aresta_app`) nem ferramentas para gestão de anexos no editor desktop (`aresta_db`).

## What Changes

- **Extração e Armazenamento Local de Anexos**:
  - Extração das páginas 69 e 70 do `croqui_original.pdf` de São João Del Rei (`database/br_mg_sao_joao_del_rei_serra_do_lenheiro/`) em PDFs individuais e limpos: `anexos/ficha_autorizacao_cemonta.pdf` e `anexos/termo_reconhecimento_riscos_cemonta.pdf`.
  - Atualização do documento `anexo_regras_cemonta.md` para apontar diretamente para os arquivos relativos locais (`anexos/*.pdf`) no formato Markdown padrão de links/botões.
- **Pipeline de Deploy e Manifesto Serving (`deploy_generated.py`)**:
  - Suporte ao diretório `anexos/`: cópia automática para `generated/<croqui_id>/anexos/`.
  - Cálculo de checksum SHA-256 de todos os arquivos contidos em `anexos/`, indexando-os no campo Protobuf `Croqui.arquivos_externos`.
  - Inclusão automática dos caminhos e hashes de `anexos/` no manifesto `generated/arquivos_serving.yaml`.
  - Atualização do cálculo de tamanho de download offline (`calcular_tamanho_croqui_bytes`) para incluir os anexos.
- **Sincronização e Serving (`serving/update_serving.py`)**:
  - Reconhecimento explícito de tipos MIME de documentos (como `.pdf` -> `application/pdf` e `.docx`) para upload com cabeçalho `Content-Type` correto no Cloudflare R2 / S3.
- **Interface Gráfica do Editor (`editor/`)**:
  - Inclusão do botão "🔘 Inserir Botão" no cabeçalho do editor de Markdown (`WidgetEditorMarkdown`), ao lado de "🖼️ Inserir Imagem".
  - Diálogo modal `DialogoInserirBotaoMarkdown` para seleção de anexo existente em `anexos/`, importação de novos arquivos externos com cópia para o croqui, ou links web externos.
  - Comando `CmdInserirBotaoMarkdown` com gestão transacional de arquivos e histórico de Undo/Redo na pilha global (`QUndoCommand`).
- **Suporte no Aplicativo Móvel (`aresta_app`)**:
  - Adição da dependência `open_filex` para despacho seguro de arquivos aos visualizadores padrão do sistema operacional (usando `FileProvider` no Android e `UIDocumentInteractionController`/QuickLook no iOS).
  - Criação do `ProvedorAnexoAresta` com arquitetura em 3 camadas (Armazenamento permanente offline -> Cache temporário volátil com hash SHA-256 -> Streaming CDN HTTP com gravação atômica).
  - Renderização enriquecida no `OfflineMarkdown` estilizando links para anexos como botões interativos e interceptando cliques para resolução e abertura imediata.

## Capabilities

### New Capabilities
- `anexos-documentos-croquis`: Armazenamento de arquivos anexos (PDFs, formulários, termos) no banco de dados, cópia para a pasta de saída, indexação em `Croqui.arquivos_externos`, integração ao manifesto `arquivos_serving.yaml` e upload com Content-Type apropriado no pipeline de serving.
- `editor-inserir-botao-markdown`: Diálogo e barra de ferramentas no editor desktop para inserção de botões de ação e documentos anexos em campos Markdown, com suporte a drag-and-drop, cópia de arquivos para a pasta do croqui e histórico Undo/Redo.

### Modified Capabilities
<!-- Nenhuma capabilidade existente tem seus requisitos funcionais alterados; novas funcionalidades são aditivas -->

## Impact

- **Database**: Adiciona pasta `anexos/` no croqui `br_mg_sao_joao_del_rei_serra_do_lenheiro`.
- **Pipeline de Build & Deploy**: `scripts/deploy_generated.py` passa a processar pastas `anexos/` e preencher `arquivos_serving.yaml` e `Croqui.arquivos_externos`.
- **Serving**: `serving/update_serving.py` adiciona tratamento do Content-Type `application/pdf`.
- **Editor**: Adiciona `DialogoInserirBotaoMarkdown`, `CmdInserirBotaoMarkdown` e novo botão na toolbar do `WidgetEditorMarkdown`.
- **Frontend (`aresta_app`)**: Introduz `open_filex`, `ProvedorAnexoAresta` e integração com `OfflineMarkdown`.
- **Compatibilidade**: Totalmente retrocompatível; croquis sem pasta `anexos/` continuam compilando e publicando identicamente.
