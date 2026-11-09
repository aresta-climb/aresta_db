# catalogo-sqlite-delta-sync Specification

## MODIFIED Requirements

### Requirement: Estrutura e geração do catálogo SQLite
O pipeline de compilação SHALL gerar um banco de dados SQLite denominado `catalogo.db` contendo as tabelas `catalogo_croquis`, `catalogo_aresta`, `catalogo_nos_estrada`, `catalogo_distancias_estrada` e `catalogo_meta` definidas pelo esquema canônico `aresta_api/sql/catalogo.sql` (consumido via artefato gerado `aresta_api/sql/generated/catalogo_sql.py`), onde `catalogo_aresta` armazena de forma normalizada todas as entidades endereçáveis por UID (`escalada`, `setor`, `grupo` e `botao`) referenciando `setor_uid` e `grupo_uid` sem duplicar nomes de setores ou grupos, `catalogo_nos_estrada` e `catalogo_distancias_estrada` armazenam a malha rodoviária pré-computada por `croqui_uid`, e o conjunto é versionado por um hash lógico determinístico (`versao_catalogo`) registrado na mensagem `Indice` (`indice.binarypb`).

#### Scenario: Geração bem-sucedida a partir de croquis compilados
- **WHEN** o pipeline de compilação processa a lista de croquis do banco de dados
- **THEN** o arquivo `catalogo.db` é inicializado com o DDL canônico de `aresta_api` e preenchido contendo todos os croquis em `catalogo_croquis`, todas as entidades endereçáveis (`escalada`, `setor`, `grupo` e `botao`) em `catalogo_aresta` e a malha rodoviária em `catalogo_nos_estrada` e `catalogo_distancias_estrada`, além da `versao_catalogo` gravada em `catalogo_meta` e no `indice.binarypb`.

#### Scenario: Indexação de busca e chaves primárias
- **WHEN** as tabelas do catálogo são criadas a partir do DDL gerado pelo `aresta_api`
- **THEN** a tabela `catalogo_croquis` possui chave primária em `croqui_uid`, a tabela `catalogo_aresta` possui chave primária em `uid` e índices em `croqui_uid`, `nome COLLATE NOCASE` e `tipo`, `catalogo_nos_estrada` possui chave primária em `no_osm_id`, `catalogo_distancias_estrada` possui chave primária composta `(croqui_uid, no_osm_id)` e índice em `no_osm_id`, e `catalogo_meta` possui chave primária em `chave`.

#### Scenario: Determinismo do hash lógico da versão
- **WHEN** o catálogo contém exatamente os mesmos registros de croquis, entidades e malha rodoviária em duas execuções distintas (seja compilação integral ou incremental)
- **THEN** o hash `versao_catalogo` calculado sobre as linhas ordenadas é estritamente idêntico.

### Requirement: Atualização seletiva e incremental de croquis
O gerador do catálogo SHALL suportar modo incremental para compilações parciais ou totais, substituindo em `catalogo_croquis` e `catalogo_aresta` apenas os registros dos croquis cujos metadados de catálogo tenham efetivamente mudado, preservando a malha rodoviária já existente em `catalogo_distancias_estrada` quando a localização do pico não for alterada, removendo croquis e nós rodoviários órfãos e preservando o arquivo `catalogo.db` sem escritas quando nenhum dado lógico do catálogo for alterado.

#### Scenario: Atualização de croqui específico
- **WHEN** o deploy é invocado passando um ou mais croquis alvos via parâmetro cujos dados de catálogo foram modificados
- **THEN** os registros anteriores dos croquis modificados são atualizados atomicamente em `catalogo_croquis` e `catalogo_aresta` (preservando sua malha em `catalogo_distancias_estrada` caso já calculada) e `versao_catalogo` é recalculada em `catalogo_meta`.

#### Scenario: Preservação de croquis inalterados
- **WHEN** um deploy parcial é executado em um banco de dados existente
- **THEN** os registros de croquis e distâncias rodoviárias que não estavam na lista de alvos permanecem inalterados no `catalogo.db`.

#### Scenario: Imutabilidade do banco quando dados de catálogo do croqui alvo não mudam
- **WHEN** um croqui já presente no `catalogo.db` é recompilado (por exemplo, após edição exclusiva de pontos de interesse em mapas ou descrições Markdown) sem qualquer alteração nos campos de `catalogo_croquis`, nas linhas de `catalogo_aresta` ou na malha rodoviária daquele `croqui_uid`
- **THEN** o gerador não remove nem reinsere o croqui e mantém os bytes do arquivo `catalogo.db` inalterados.

#### Scenario: Remoção de croquis órfãos em compilação completa
- **WHEN** a geração completa do catálogo (`alvos=None`) é executada sobre um `catalogo.db` existente que contém um `croqui_uid` cuja pasta compilada não existe mais no diretório `generated/`
- **THEN** os registros daquele `croqui_uid` são removidos de `catalogo_croquis`, `catalogo_aresta` e `catalogo_distancias_estrada`, quaisquer `no_osm_id` em `catalogo_nos_estrada` que fiquem sem nenhuma referência em `catalogo_distancias_estrada` são expurgados, e `versao_catalogo` é atualizada.

### Requirement: Extração de deltas SQL versionados para o Cloudflare D1
O sistema SHALL disponibilizar utilitário para calcular as diferenças entre duas versões do catálogo SQLite gerando comandos de inserção, atualização e remoção (`upserts` e `deletes`) para croquis, entidades, nós de estrada e distâncias de estrada, serializáveis em JSON acompanhados do `versao_hash` de destino para alimentação da tabela `deltas_catalogo` no D1.

#### Scenario: Cálculo de deltas entre versões
- **WHEN** o script de deltas compara uma versão anterior do `catalogo.db` com uma nova versão
- **THEN** os croquis, entidades, nós rodoviários e distâncias rodoviárias novos ou modificados são identificados como upserts e os removidos são identificados como deletes.

#### Scenario: Formato compatível com o endpoint de sincronização
- **WHEN** o changeset de deltas é gerado
- **THEN** a saída estruturada inclui o `versao_hash` da versão nova e os campos `nos_estrada` e `distancias_estrada` em conformidade com `UpsertsSyncCatalogo` e `DeletesSyncCatalogo`, permitindo a inserção direta na tabela `deltas_catalogo` do Cloudflare D1.
