## ADDED Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair vídeos e postagens candidatas para uma dada via de escalada usando uma malha tripla: YouTube Data API v3, Vertex AI Search e duckduckgo-search (para instagram.com).

#### Scenario: Busca bem sucedida por vídeos
- **WHEN** o worker recebe uma lista de escaladas (Nome da Via, Setor, Pico) estruturadas
- **THEN** ele compila múltiplas queries de pesquisa.
- **THEN** ele retorna uma lista não-filtrada de mídias candidatas contendo URL da mídia, título do post/vídeo, snippet textual da busca e URL da thumbnail.
