## Why

O banco de dados de croquis estáticos agora está estruturado e estaticamente tipado em Protobuf, mas lhe falta a riqueza da informação dinâmica (como vídeos e postagens em mídias sociais mostrando a execução das escaladas). Extrair vídeos e posts do YouTube e do Instagram de forma semi-automatizada transformará nosso "catálogo de vias" em uma rica **Base de Conhecimento Semântica de Escalada** e pavimentará o caminho para um assistente de IA (RAG) direto no app no futuro.

## What Changes

- Criação de um novo workflow interativo no Antigravity (`/coletar_betas`).
- Implementação de workers de busca consumindo as APIs do **YouTube Data API v3**, **Vertex AI Search** e **duckduckgo-search** para garantir uma malha ampla de captura.
- Desenvolvimento de um pipeline de **sub-agentes LLM** focado não apenas em dar um "Score de Confiança" para o resultado, mas em **extrair metadados e resumos** sobre o movimento chave da via (Beta) a partir da descrição do vídeo.
- Adição de uma aba de **"Aprovação de Betas" no Editor PyQt** atual, capaz de renderizar thumbnails remotas e permitir aprovação/rejeição humana com transparência total.
- **Persistência na Origem**: O salvamento das mídias modificará os arquivos Markdown/YAML originais (fonte da verdade) dos setores, para que a geração sequencial do `compilado.binarypb` incorpore as mídias perfeitamente no sub-proto de cada via.

## Capabilities

### New Capabilities
- `media-scraping`: Orquestração de chamadas à YouTube Data API v3, Vertex AI Search e duckduckgo-search.
- `beta-intelligence`: Sub-agentes responsáveis por dar nota de relevância e extrair dados semânticos dos snippets da busca (ex: resumos do crux).
- `curation-panel`: Aba de curadoria no app PyQt para visualização em grid com rendering HTTP nativo de thumbnails e interface de validação.
- `beta-model`: Expansão da ontologia de dados (Protobuf e esquema Markdown) para suportar mídias ricas (`MidiaBeta` e `MetaBeta`).

### Modified Capabilities
- Nenhuma. As capacidades atuais de conversão PDF->Protobuf permanecem intactas, a coleta de betas é um processo suplementar que roda após (ou de forma pontual independente).

## Impact

- **Protobuf**: O schema central precisará de novas sub-messages (`MidiaBeta`, `MetaBeta`).
- **Editor PyQt**: A aplicação de curadoria ganhará uma dependência leve de requisições de rede (para thumbnails) e uma aba inteira de validação, além da rotina de edição in-place de blocos YAML dentro de arquivos Markdown já existentes.
- **Custos Operacionais Cloud**: Introduz custo base nulo no Google Cloud Platform (a API do Vertex AI Search possui um tier generoso de 10.000 requisições gratuitas por mês).
