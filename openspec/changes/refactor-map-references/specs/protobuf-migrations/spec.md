## ADDED Requirements

### Requirement: Documentação de Política de Migrações
O sistema SHALL possuir documentação explícita na pasta `docs/` sobre a política de execução e criação de scripts de migração, de forma a instruir desenvolvedores sobre como lidar com quebras de schema (breaking changes) no `croqui.proto`.

#### Scenario: Consulta à documentação de migração
- **WHEN** um desenvolvedor precisa introduzir uma breaking change
- **THEN** ele lê a documentação em `docs/politica_migracoes.md` (ou similar) para entender como nomear o arquivo de migração (ex: `0002_descricao.py`) e como testá-lo
