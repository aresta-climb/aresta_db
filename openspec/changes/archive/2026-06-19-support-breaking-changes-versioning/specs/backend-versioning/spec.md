## ADDED Requirements

### Requirement: Exportação Versionada de Dados
O script de compilação ou exportação (`build.py` ou similar) SHALL exportar os arquivos gerados (como `indice.pb` e a pasta `croquis/` em Protobuf, provenientes da pasta `generated`) para dentro de um subdiretório nomeado de acordo com a versão atual de schema do banco, em vez da raiz da pasta de exportação.

#### Scenario: Exportando dados quando a migração atual for a número 15
- **WHEN** o comando de build ou exportação é rodado
- **THEN** os arquivos finais devem ser colocados em uma pasta `v15` (ex: `output/v15/indice.pb` e `output/v15/croquis/...`)

### Requirement: Deploy Não-Destrutivo
O pipeline de deploy (Github Actions) SHALL enviar apenas os arquivos da versão atual para o bucket R2 via sincronização delta (S3 sync), sem apagar ou sobrescrever os diretórios de versões anteriores.

#### Scenario: Atualizando a versão servida de v14 para v15
- **WHEN** o pipeline de deploy for acionado contendo os dados na pasta `v15`
- **THEN** o bucket R2 deverá receber os novos dados na pasta `v15/`, mantendo a pasta `v14/` e seu conteúdo intactos para clientes antigos.
