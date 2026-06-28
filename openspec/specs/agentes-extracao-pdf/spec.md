# agentes-extracao-pdf Specification

## Purpose
TBD - created by syncing from change mapas-interativos. Update Purpose after archive.

## Requirements

### Requirement: Geração de Frontmatter exclusivo para Mapas Gerais
O agente extrator (`ConversorMarkdown`) MUST criar o arquivo `mapas_gerais.md` apenas com conteúdo YAML Frontmatter, preenchendo a chave `mapas` de acordo com a extração de imagens. O corpo do markdown DEVE ser vazio.

#### Scenario: Processando um PDF de mapa geral
- **WHEN** o arquivo recebido for do tipo `mapas_gerais`
- **THEN** o agente gerará o `mapas_gerais.md` com `mapas: [caminho_imagem_mapa: ...]` e nenhum texto associado
