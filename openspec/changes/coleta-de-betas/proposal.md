## Why

O banco de dados de croquis estáticos agora está estruturado e estaticamente tipado em Protobuf, mas lhe falta a riqueza da informação dinâmica (como vídeos e postagens em mídias sociais mostrando a execução das escaladas). Extrair vídeos e posts do YouTube e do Instagram de forma semi-automatizada transformará nosso "catálogo de vias" em uma rica **Base de Conhecimento Semântica de Escalada** e pavimentará o caminho para um assistente de IA (RAG) direto no app no futuro.

## What Changes

- **Módulo Auto-Contido (`coleta_de_betas/`)**: Todo o código da nova funcionalidade (extratores, inteligência LLM, componentes de curadoria PyQt, persistência e testes) será implementado de forma isolada e modular dentro de um diretório dedicado de primeiro nível `coleta_de_betas/`.
- Criação de um schema Protobuf dedicado (`beta.proto`) para suportar `MidiaBeta`, `MetaBeta` e a mensagem raiz `BetasPendentes` (usada no arquivo intermediário `betas_pendentes.binarypb`), importado posteriormente em `croqui.proto`.
- Criação de um novo workflow interativo no Antigravity (`/coletar_betas`).
- Implementação de workers de busca consumindo as APIs do **YouTube Data API v3**, **Vertex AI Search** e **duckduckgo-search** para garantir uma malha ampla de captura.
- Desenvolvimento de um pipeline de **sub-agentes LLM** focado não apenas em dar um "Score de Confiança" para o resultado, mas em **extrair metadados e resumos** sobre o movimento chave da via (Beta) a partir da descrição do vídeo.
- Adição de uma aba de **"Aprovação de Betas" no Editor PyQt** atual (reutilizando os componentes de `coleta_de_betas/curadoria/`), capaz de renderizar thumbnails remotas e permitir aprovação/rejeição humana com transparência total.
- **Persistência na Origem**: O salvamento das mídias modificará os arquivos Markdown/YAML originais (fonte da verdade) dos setores, para que a geração sequencial do `compilado.binarypb` incorpore as mídias perfeitamente no sub-proto de cada via.
- **Monitoramento de Saúde**: Adição de uma coluna no `STATUS_CROQUIS.md` (via `scripts/medir_saude_croquis.py`) indicando se há betas pendentes de aprovação (estado de alerta/ruim).

## Capabilities

### New Capabilities
- `media-scraping`: Orquestração de chamadas à YouTube Data API v3, Vertex AI Search e duckduckgo-search.
- `beta-intelligence`: Sub-agentes responsáveis por dar nota de relevância e extrair dados semânticos dos snippets da busca (ex: resumos do crux).
- `curation-panel`: Aba de curadoria no app PyQt para visualização em grid com rendering HTTP nativo de thumbnails e interface de validação.
- `beta-model`: Expansão da ontologia de dados com arquivo dedicado `beta.proto` e esquema Markdown para suportar mídias ricas (`MidiaBeta`, `MetaBeta` e `BetasPendentes`).
- `beta-health-check`: Monitoramento e coluna no relatório `STATUS_CROQUIS.md` sinalizando croquis com pendências de curadoria de betas.

### Modified Capabilities
- Nenhuma. As capacidades atuais de conversão PDF->Protobuf permanecem intactas, a coleta de betas é um processo suplementar que roda após (ou de forma pontual independente).

## Impact

- **Organização de Código**: Novo módulo auto-contido de primeiro nível `coleta_de_betas/`, contendo seus próprios submódulos e suíte de testes.
- **Protobuf**: Novo arquivo de schema `beta.proto` independente, posteriormente importado por `croqui.proto`.
- **Editor PyQt**: A aplicação de curadoria importará os widgets/controllers de `coleta_de_betas.curadoria`, com uma aba inteira de validação.
- **Relatório de Saúde**: `scripts/medir_saude_croquis.py` e `STATUS_CROQUIS.md` ganham coluna e checagem de pendência de betas.
- **Custos Operacionais Cloud**: Custo base nulo no Google Cloud Platform (a API do Vertex AI Search possui um tier generoso de 10.000 requisições gratuitas por mês).
