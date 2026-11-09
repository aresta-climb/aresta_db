# Spec Delta

## MODIFIED Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair vídeos, postagens e artigos de blog candidatos para as escaladas selecionadas usando YouTube Data API v3, Vertex AI Search e o pacote `ddgs` (para Instagram e páginas de blog), sem emitir avisos de depreciação (`RuntimeWarning`) e ignorando URLs que já constem em qualquer uma das 4 listas da escalada (`betas`, `betas_nao_revisados`, `betas_nao_scorados` e `betas_rejeitados`).

#### Scenario: Busca web via pacote `ddgs` sem RuntimeWarning
- **WHEN** o coletor consulta o buscador web padrão (`_BuscadorDuckDuckGoPadrao`) para localizar postagens do Instagram ou artigos de blog
- **THEN** o sistema MUST utilizar `from ddgs import DDGS` (declarado nos grupos `editor` e `pdf` do `pyproject.toml`) sem disparar `RuntimeWarning` de renomeação do pacote `duckduckgo_search`.
