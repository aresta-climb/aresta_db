# Spec Delta

## MODIFIED Requirements

### Requirement: Estrutura e geração do catálogo SQLite
O pipeline de compilação SHALL gerar um banco de dados SQLite denominado `catalogo.db` contendo as tabelas `catalogo_croquis`, `catalogo_aresta` e `catalogo_meta`, onde `catalogo_aresta` armazena de forma normalizada todas as entidades endereçáveis por UID (`escalada`, `setor`, `grupo` e `botao`) referenciando `setor_uid` e `grupo_uid` sem duplicar nomes de setores ou grupos, e versionadas por um hash lógico determinístico (`versao_catalogo`) registrado na mensagem `Indice` (`indice.binarypb`).

#### Scenario: Geração bem-sucedida a partir de croquis compilados
- **WHEN** o pipeline de compilação processa a lista de croquis do banco de dados
- **THEN** o arquivo `catalogo.db` é gerado contendo todos os croquis em `catalogo_croquis` e todas as entidades endereçáveis (`escalada`, `setor`, `grupo` e `botao`) em `catalogo_aresta` com seus respectivos `uid`, `tipo`, `croqui_uid`, `nome`, `escalada_grau`, `escalada_tipo` (`'esportiva'`, `'tradicional'`, `'boulder'`, `'multienfiada'` ou `'highline'`), `setor_uid` e `grupo_uid`, além da `versao_catalogo` gravada em `catalogo_meta` e no `indice.binarypb`.

#### Scenario: Indexação de busca e chaves primárias
- **WHEN** as tabelas do catálogo são criadas
- **THEN** a tabela `catalogo_croquis` possui chave primária em `croqui_uid`, a tabela `catalogo_aresta` possui chave primária em `uid` e índices em `croqui_uid`, `nome COLLATE NOCASE` e `tipo`, e `catalogo_meta` possui chave primária em `chave`.

#### Scenario: Determinismo do hash lógico da versão
- **WHEN** o catálogo contém exatamente os mesmos registros de croquis e entidades em duas execuções distintas (seja compilação integral ou incremental)
- **THEN** o hash `versao_catalogo` calculado sobre as linhas ordenadas é estritamente idêntico.

### Requirement: Resolução de links e metadados para aresta.cc
A estrutura dos dados nas tabelas `catalogo_aresta` e `catalogo_croquis` SHALL permitir que qualquer `uid` (`escalada`, `setor`, `grupo` ou `botao`) seja resolvido e enriquecido com os nomes de seu setor, grupo e croqui através de `LEFT JOIN` por chave primária sem depender de decodificação de Protobuf.

#### Scenario: Consulta de metadados para via de escalada
- **WHEN** um link curto `https://aresta.cc/<uid>` de uma via é acessado
- **THEN** uma consulta com `LEFT JOIN` em `catalogo_aresta` (por `setor_uid` e `grupo_uid`) e `catalogo_croquis` (por `croqui_uid`) retorna nome da via, `escalada_grau`, `escalada_tipo`, nome do setor, nome do grupo, nome do pico e estado (UF) em uma única operação.

#### Scenario: Consulta de metadados para croqui ou pico
- **WHEN** um link curto `https://aresta.cc/<croqui_uid>` de um croqui é acessado
- **THEN** uma consulta direta na tabela `catalogo_croquis` retorna o nome do pico, cidade e estado em uma única operação.
