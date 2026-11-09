## MODIFIED Requirements

### Requirement: Sincronização transacional com Cloudflare D1 durante o deploy
O script de deploy de serving (`serving/update_serving.py`) SHALL sincronizar automaticamente o estado do catálogo e registrar o delta no Cloudflare D1 via API REST antes de atualizar o arquivo `catalogo.db` no Cloudflare R2, utilizando os esquemas DDL canônicos (`catalogo.sql` e `catalogo_d1.sql`) e os contratos de payload gerados pelo `aresta_api`, sem depender da instalação de `google.protobuf` ou da importação de `scripts/gerar_malha_estrada_lib.py`.

#### Scenario: Deploy incremental com alterações no catálogo
- **WHEN** o `update_serving.py` detecta mudanças no catálogo em relação ao estado publicado
- **THEN** o script baixa o `catalogo.db` anterior do R2, calcula os deltas, aplica os upserts e deletes em `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada` e `catalogo_distancias_estrada` no D1, insere o registro na tabela `deltas_catalogo` com o `versao_hash` e somente após o sucesso atualiza o R2 e purga o cache da CDN.

#### Scenario: Execução do deploy sem dependência de Protobuf ou do gerador de malha OSM
- **WHEN** `serving/update_serving.py` é importado e executado em um ambiente Python sem o pacote `google.protobuf` e sem `scripts/gerar_malha_estrada_lib.py`
- **THEN** a leitura de versão do `catalogo.db`, o cálculo de deltas e a sincronização com o Cloudflare D1 e R2 são concluídos sem `ModuleNotFoundError`.

#### Scenario: Bootstrap inicial ou banco D1 vazio
- **WHEN** a tabela `deltas_catalogo` do Cloudflare D1 está vazia ou seu último `versao_hash` não corresponde ao `catalogo.db` anterior do R2
- **THEN** o sincronizador inicializa o esquema D1 usando o DDL canônico gerado por `aresta_api` (`catalogo.sql` e `catalogo_d1.sql`), realiza o bootstrap completo das tabelas `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada` e `catalogo_distancias_estrada` no D1 a partir do `generated/catalogo.db` local e registra a versão inicial em `deltas_catalogo`.

#### Scenario: Falha na sincronização com o D1 preserva o R2
- **WHEN** a comunicação ou execução SQL na API REST do Cloudflare D1 falha durante o deploy
- **THEN** o script interrompe a execução antes de substituir o `catalogo.db` e o `arquivos_serving.yaml` no R2, garantindo que a próxima execução possa recalcular o diff sem perda de dados.
