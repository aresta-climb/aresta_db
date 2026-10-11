# Spec Delta

## Purpose

Fornece a geração e sincronização contínua de um banco SQLite compacto contendo os metadados de croquis e escaladas, viabilizando busca textual offline instantânea no aplicativo e resolução eficiente de links curtos e QR Codes na borda com OpenGraph.

## ADDED Requirements

### Requirement: Estrutura e geração do catálogo SQLite
O pipeline de compilação SHALL gerar um banco de dados SQLite denominado `catalogo.db` contendo as tabelas `catalogo_croquis` e `catalogo_aresta`, indexadas para consultas rápidas por identificador e termos textuais.

#### Scenario: Geração bem-sucedida a partir de croquis compilados
- **WHEN** o pipeline de compilação processa a lista de croquis do banco de dados
- **THEN** o arquivo `catalogo.db` é gerado contendo todos os croquis e escaladas catalogadas com seus respectivos identificadores estáveis (UIDs).

#### Scenario: Indexação de busca e chaves primárias
- **WHEN** as tabelas do catálogo são criadas
- **THEN** a tabela `catalogo_croquis` possui chave primária em `croqui_uid` e a tabela `catalogo_aresta` possui chave primária em `uid` e índice em `croqui_uid`.

### Requirement: Atualização seletiva e incremental de croquis
O gerador do catálogo SHALL suportar modo incremental para compilações parciais, substituindo apenas os registros dos croquis modificados sem corromper ou descartar os dados dos demais croquis existentes no banco.

#### Scenario: Atualização de croqui específico
- **WHEN** o deploy é invocado passando um ou mais croquis alvos via parâmetro
- **THEN** os registros anteriores dos croquis correspondentes são removidos de `catalogo_croquis` e `catalogo_aresta` e os novos registros são inseridos atomicamente.

#### Scenario: Preservação de croquis inalterados
- **WHEN** um deploy parcial é executado em um banco de dados existente
- **THEN** os registros de croquis que não estavam na lista de alvos permanecem inalterados no `catalogo.db`.

### Requirement: Compressão e integração no manifesto de serving
O pipeline SHALL produzir uma versão compactada `catalogo.db.gz` e registrar ambos os artefatos com seus respectivos hashes SHA-256 no manifesto `arquivos_serving.yaml`.

#### Scenario: Compressão gzip do catálogo
- **WHEN** o arquivo `catalogo.db` é gerado ou atualizado
- **THEN** um arquivo correspondente `catalogo.db.gz` é gerado na mesma pasta de saída.

#### Scenario: Registro no manifesto de serving
- **WHEN** o manifesto `arquivos_serving.yaml` é construído no Passo D
- **THEN** as entradas `catalogo.db` e `catalogo.db.gz` são incluídas com seus respectivos hashes SHA-256.

### Requirement: Extração de deltas SQL versionados para o Cloudflare D1
O sistema SHALL disponibilizar utilitário para calcular as diferenças entre duas versões do catálogo SQLite gerando comandos de inserção, atualização e remoção (`upserts` e `deletes`) serializáveis em JSON para alimentação da tabela `deltas_catalogo` no D1.

#### Scenario: Cálculo de deltas entre versões
- **WHEN** o script de deltas compara uma versão anterior do `catalogo.db` com uma nova versão
- **THEN** as vias e croquis novos ou modificados são identificados como upserts e os removidos são identificados como deletes.

#### Scenario: Formato compatível com o endpoint de sincronização
- **WHEN** o changeset de deltas é gerado
- **THEN** a saída estruturada permite a inserção direta na tabela `deltas_catalogo` do Cloudflare D1 com versionamento incremental autoincrement.

### Requirement: Resolução de links e metadados para aresta.cc
A estrutura dos dados nas tabelas `catalogo_aresta` e `catalogo_croquis` SHALL permitir que o worker de borda resolva qualquer `uid` através de um `JOIN` simples e renderize meta tags OpenGraph e Twitter Cards sem depender de decodificação de Protobuf.

#### Scenario: Consulta de metadados para via de escalada
- **WHEN** um link curto `https://aresta.cc/<uid>` de uma via é acessado
- **THEN** uma consulta combinando `catalogo_aresta` e `catalogo_croquis` retorna nome da via, graduação, tipo, setor, nome do pico e estado (UF) em uma única operação.

#### Scenario: Consulta de metadados para croqui ou pico
- **WHEN** um link curto `https://aresta.cc/<croqui_uid>` de um croqui é acessado
- **THEN** uma consulta direta na tabela `catalogo_croquis` retorna o nome do pico, cidade e estado em uma única operação.
