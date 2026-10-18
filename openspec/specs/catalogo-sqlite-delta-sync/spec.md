# catalogo-sqlite-delta-sync Specification

## Purpose

Fornece a geração e sincronização contínua de um banco SQLite compacto contendo os metadados de croquis e escaladas, viabilizando busca textual offline instantânea no aplicativo e resolução eficiente de links curtos e QR Codes na borda com OpenGraph.

## Requirements

### Requirement: Estrutura e geração do catálogo SQLite
O pipeline de compilação SHALL gerar um banco de dados SQLite denominado `catalogo.db` contendo as tabelas `catalogo_croquis`, `catalogo_aresta` e `catalogo_meta` definidas pelo esquema canônico `aresta_api/sql/catalogo.sql` (consumido via artefato gerado `aresta_api/sql/generated/catalogo_sql.py`), onde `catalogo_aresta` armazena de forma normalizada todas as entidades endereçáveis por UID (`escalada`, `setor`, `grupo` e `botao`) referenciando `setor_uid` e `grupo_uid` sem duplicar nomes de setores ou grupos, e versionadas por um hash lógico determinístico (`versao_catalogo`) registrado na mensagem `Indice` (`indice.binarypb`).

#### Scenario: Geração bem-sucedida a partir de croquis compilados
- **WHEN** o pipeline de compilação processa a lista de croquis do banco de dados
- **THEN** o arquivo `catalogo.db` é inicializado com o DDL canônico de `aresta_api` e preenchido contendo todos os croquis em `catalogo_croquis` e todas as entidades endereçáveis (`escalada`, `setor`, `grupo` e `botao`) em `catalogo_aresta` com seus respectivos `uid`, `tipo`, `croqui_uid`, `nome`, `escalada_grau`, `escalada_tipo` (`'esportiva'`, `'tradicional'`, `'boulder'`, `'multienfiada'` ou `'highline'`), `setor_uid` e `grupo_uid`, além da `versao_catalogo` gravada em `catalogo_meta` e no `indice.binarypb`.

#### Scenario: Indexação de busca e chaves primárias
- **WHEN** as tabelas do catálogo são criadas a partir do DDL gerado pelo `aresta_api`
- **THEN** a tabela `catalogo_croquis` possui chave primária em `croqui_uid`, a tabela `catalogo_aresta` possui chave primária em `uid` e índices em `croqui_uid`, `nome COLLATE NOCASE` e `tipo`, e `catalogo_meta` possui chave primária em `chave`.

#### Scenario: Determinismo do hash lógico da versão
- **WHEN** o catálogo contém exatamente os mesmos registros de croquis e entidades em duas execuções distintas (seja compilação integral ou incremental)
- **THEN** o hash `versao_catalogo` calculado sobre as linhas ordenadas é estritamente idêntico.

### Requirement: Atualização seletiva e incremental de croquis
O gerador do catálogo SHALL suportar modo incremental para compilações parciais ou totais, substituindo em `catalogo_croquis` e `catalogo_aresta` apenas os registros dos croquis cujos metadados de catálogo tenham efetivamente mudado, removendo croquis órfãos em compilações totais e preservando o arquivo `catalogo.db` (incluindo `atualizado_em`) sem escritas quando nenhum dado lógico do catálogo for alterado.

#### Scenario: Atualização de croqui específico
- **WHEN** o deploy é invocado passando um ou mais croquis alvos via parâmetro cujos dados de catálogo foram modificados
- **THEN** os registros anteriores dos croquis modificados são removidos de `catalogo_croquis` e `catalogo_aresta`, os novos registros são inseridos atomicamente e `versao_catalogo` é recalculada em `catalogo_meta`.

#### Scenario: Preservação de croquis inalterados
- **WHEN** um deploy parcial é executado em um banco de dados existente
- **THEN** os registros de croquis que não estavam na lista de alvos permanecem inalterados no `catalogo.db`.

#### Scenario: Imutabilidade do banco quando dados de catálogo do croqui alvo não mudam
- **WHEN** um croqui já presente no `catalogo.db` é recompilado (por exemplo, após edição exclusiva de pontos de interesse em mapas ou descrições Markdown) sem qualquer alteração nos campos de `catalogo_croquis` (`croqui_uid, id_slug, nome, cidade, estado`) ou nas linhas de `catalogo_aresta` daquele `croqui_uid`
- **THEN** o gerador não remove nem reinsere o croqui, preserva o valor anterior de `atualizado_em` na tabela `catalogo_croquis` e mantém os bytes do arquivo `catalogo.db` inalterados.

#### Scenario: Remoção de croquis órfãos em compilação completa
- **WHEN** a geração completa do catálogo (`alvos=None`) é executada sobre um `catalogo.db` existente que contém um `croqui_uid` cuja pasta compilada não existe mais no diretório `generated/`
- **THEN** os registros daquele `croqui_uid` são removidos de `catalogo_croquis` e `catalogo_aresta` e `versao_catalogo` é atualizada.

### Requirement: Extração de deltas SQL versionados para o Cloudflare D1
O sistema SHALL disponibilizar utilitário para calcular as diferenças entre duas versões do catálogo SQLite gerando comandos de inserção, atualização e remoção (`upserts` e `deletes`) serializáveis em JSON acompanhados do `versao_hash` de destino para alimentação da tabela `deltas_catalogo` no D1.

#### Scenario: Cálculo de deltas entre versões
- **WHEN** o script de deltas compara uma versão anterior do `catalogo.db` com uma nova versão
- **THEN** as entidades e croquis novos ou modificados são identificados como upserts e os removidos são identificados como deletes.

#### Scenario: Formato compatível com o endpoint de sincronização
- **WHEN** o changeset de deltas é gerado
- **THEN** a saída estruturada inclui o `versao_hash` da versão nova e permite a inserção direta na tabela `deltas_catalogo` do Cloudflare D1.

### Requirement: Resolução de links e metadados para aresta.cc
A estrutura dos dados nas tabelas `catalogo_aresta` e `catalogo_croquis` SHALL permitir que qualquer `uid` (`escalada`, `setor`, `grupo` ou `botao`) seja resolvido e enriquecido com os nomes de seu setor, grupo e croqui através de `LEFT JOIN` por chave primária sem depender de decodificação de Protobuf.

#### Scenario: Consulta de metadados para via de escalada
- **WHEN** um link curto `https://aresta.cc/<uid>` de uma via é acessado
- **THEN** uma consulta com `LEFT JOIN` em `catalogo_aresta` (por `setor_uid` e `grupo_uid`) e `catalogo_croquis` (por `croqui_uid`) retorna nome da via, `escalada_grau`, `escalada_tipo`, nome do setor, nome do grupo, nome do pico e estado (UF) em uma única operação.

#### Scenario: Consulta de metadados para croqui ou pico
- **WHEN** um link curto `https://aresta.cc/<croqui_uid>` de um croqui é acessado
- **THEN** uma consulta direta na tabela `catalogo_croquis` retorna o nome do pico, cidade e estado em uma única operação.

### Requirement: Recuperação de emergência e purge remoto do catálogo
O sistema SHALL prever um mecanismo de purge global via configuração remota (Firebase Remote Config) que permite forçar o descarte do banco local e o download limpo do `catalogo.db` em todos os clientes móveis.

#### Scenario: Purge remoto acionado por emergência
- **WHEN** o valor de purge remoto for maior que o timestamp do último purge executado e maior que o timestamp do build do aplicativo
- **THEN** o cliente descarta o `catalogo.db` local e efetua o download limpo do `catalogo.db` completo a partir do CDN.

#### Scenario: Primeira instalação do aplicativo com preload
- **WHEN** o aplicativo é instalado pela primeira vez trazendo o catálogo pré-embarcado como asset
- **THEN** purges emitidos remotamente antes do momento de compilação do pacote são ignorados e nenhum download é executado.

### Requirement: Sincronização transacional com Cloudflare D1 durante o deploy
O script de deploy de serving (`serving/update_serving.py`) SHALL sincronizar automaticamente o estado do catálogo e registrar o delta no Cloudflare D1 via API REST antes de atualizar o arquivo `catalogo.db` no Cloudflare R2, utilizando os esquemas DDL canônicos (`catalogo.sql` e `catalogo_d1.sql`) e os contratos de payload gerados pelo `aresta_api`.

#### Scenario: Deploy incremental com alterações no catálogo
- **WHEN** o `update_serving.py` detecta mudanças no catálogo em relação ao estado publicado
- **THEN** o script baixa o `catalogo.db` anterior do R2, calcula os deltas, aplica os upserts e deletes em `catalogo_croquis` e `catalogo_aresta` no D1, insere o registro na tabela `deltas_catalogo` com o `versao_hash` e somente após o sucesso atualiza o R2 e purga o cache da CDN.

#### Scenario: Bootstrap inicial ou banco D1 vazio
- **WHEN** a tabela `deltas_catalogo` do Cloudflare D1 está vazia ou seu último `versao_hash` não corresponde ao `catalogo.db` anterior do R2
- **THEN** o sincronizador inicializa o esquema D1 usando o DDL canônico gerado por `aresta_api` (`catalogo.sql` e `catalogo_d1.sql`), realiza o bootstrap completo das tabelas `catalogo_croquis` e `catalogo_aresta` no D1 a partir do `generated/catalogo.db` local e registra a versão inicial em `deltas_catalogo`.

#### Scenario: Falha na sincronização com o D1 preserva o R2
- **WHEN** a comunicação ou execução SQL na API REST do Cloudflare D1 falha durante o deploy
- **THEN** o script interrompe a execução antes de substituir o `catalogo.db` e o `arquivos_serving.yaml` no R2, garantindo que a próxima execução possa recalcular o diff sem perda de dados.

### Requirement: Endpoint de sincronização de deltas na borda com cache imutável
O Cloudflare Worker em `catalogo.arestaclimb.com` SHALL expor a rota `GET /sync?versao_local=<hash_local>&versao_destino=<hash_destino>` tipada pelos artefatos gerados de `aresta_api/openapi/catalogo.yaml` e `aresta_api/sql/catalogo_d1.sql`, retornando o delta condensado (Delta Squash) com cabeçalhos de cache imutável para retenção integral na CDN da Cloudflare.

#### Scenario: Sincronização entre versões válidas com Delta Squash
- **WHEN** uma requisição `GET /sync?versao_local=A&versao_destino=B` é recebida e ambas as versões existem na tabela `deltas_catalogo` com `id(A) < id(B)`
- **THEN** o Worker condensa todos os deltas intermediários por chave primária em ordem cronológica e retorna HTTP 200 em conformidade com o schema `RespostaSyncCatalogo` (`acao: "apply_delta"`, `upserts`, `deletes`) e `Cache-Control: public, max-age=31536000, s-maxage=31536000, immutable`.

#### Scenario: Fallback para download integral quando versão local é desconhecida
- **WHEN** uma requisição `GET /sync?versao_local=X&versao_destino=B` informa uma `versao_local` inexistente no D1 ou posterior à `versao_destino`
- **THEN** o Worker retorna HTTP 200 com `acao: "full_download"` e `Cache-Control: no-store`.

### Requirement: Integração do catálogo descomprimido no manifesto de serving
O pipeline SHALL manter apenas o artefato descomprimido `catalogo.db` na pasta `generated/` e registrá-lo com seu hash SHA-256 no manifesto `arquivos_serving.yaml`, delegando a compressão de transferência HTTP para a borda da CDN Cloudflare.

#### Scenario: Registro exclusivo do catálogo descomprimido no manifesto
- **WHEN** o manifesto `arquivos_serving.yaml` é construído no Passo D
- **THEN** a entrada `catalogo.db` é incluída com seu respectivo hash SHA-256 e nenhum arquivo `catalogo.db.gz` local é produzido.

### Requirement: Exportação incremental determinística do catálogo em CSV
O gerador do catálogo SHALL exportar ao lado do arquivo `catalogo.db` três arquivos CSV determinísticos em UTF-8 com quebras de linha LF (`catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`) espelhando as tabelas do banco SQLite, atualizando-os apenas quando houver mudança no conteúdo do catálogo ou quando algum dos arquivos CSV estiver ausente no disco.

#### Scenario: Geração dos três arquivos CSV espelhando as tabelas do catálogo
- **WHEN** `catalogo.db` é gerado pela primeira vez ou sofre alteração em suas tabelas
- **THEN** o sistema grava no mesmo diretório do banco os arquivos `catalogo_croquis.csv` (colunas `croqui_uid,id_slug,nome,cidade,estado` ordenadas por `id_slug, croqui_uid`), `catalogo_aresta.csv` (colunas `uid,tipo,croqui_uid,nome,escalada_grau,escalada_tipo,setor_uid,grupo_uid` ordenadas por `croqui_uid, uid`) e `catalogo_meta.csv` (colunas `chave,valor` ordenadas por `chave`).

#### Scenario: Short-circuit de escrita CSV quando o catálogo não sofre alteração
- **WHEN** o gerador do catálogo é executado, nenhuma linha de `catalogo_croquis` ou `catalogo_aresta` muda e os três arquivos CSV já existem no disco
- **THEN** o sistema não reescreve `catalogo_croquis.csv`, `catalogo_aresta.csv` nem `catalogo_meta.csv`, preservando seus timestamps de modificação no sistema de arquivos.

