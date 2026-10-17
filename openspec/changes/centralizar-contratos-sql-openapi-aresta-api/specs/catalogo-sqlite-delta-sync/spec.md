# Spec Delta

## MODIFIED Requirements

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
