## ADDED Requirements

### Requirement: Extração Tipada de Vias do Croqui
O sistema SHALL fornecer um comando e rotina em Python para extrair todas as vias e boulders de um croqui para um arquivo `vias_extraidas.yaml` validado e tipado pelo schema Protobuf `ViasExtraidasCroqui`.

#### Scenario: Extração com sucesso a partir do banco de dados
- **WHEN** o comando de extração de vias é executado para a pasta de um croqui válido
- **THEN** ele MUST ler `croqui.yaml` e os arquivos `.md` dos setores.
- **THEN** ele MUST estruturar cada via com seu `id_escalada`, `nome`, `grau`, `tipo`, `nome_setor`, `nome_grupo`, `nome_pico`, `cidade`, `estado` e `arquivo_origem`.
- **THEN** ele MUST validar e serializar o resultado em `database/<croqui>/vias_extraidas.yaml` via `ViasExtraidasCroqui`.

### Requirement: Busca Concorrente e Geração de Candidatos Brutos em YAML
O sistema SHALL executar a busca tripla concorrente (YouTube, Vertex AI Search e DuckDuckGo) a partir do `vias_extraidas.yaml` e salvar `candidatos_brutos.yaml` tipado por `BetasPendentes`.

#### Scenario: Execução de busca e serialização de candidatos
- **WHEN** o comando de busca é invocado passando o caminho do croqui e o `vias_extraidas.yaml`
- **THEN** ele MUST disparar buscas paralelas usando os metadados geográficos e de escalada para refinar as queries.
- **THEN** ele MUST deduplicar os resultados, consolidando snippets e thumbnails.
- **THEN** ele MUST salvar `database/<croqui>/candidatos_brutos.yaml` tipado e validado por `BetasPendentes`.

### Requirement: Geração do Arquivo de Staging Binário
O sistema SHALL fornecer comando e rotina para converter os candidatos avaliados em formato Protobuf binário `betas_pendentes.binarypb`.

#### Scenario: Salvamento do arquivo staging
- **WHEN** os candidatos avaliados são fornecidos
- **THEN** o sistema MUST validar a estrutura com a mensagem `BetasPendentes` e salvar `database/<croqui>/betas_pendentes.binarypb`.
