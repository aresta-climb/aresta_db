# media-scraping Specification

## Purpose
Define a malha de extratores de mídias de beta (YouTube, Instagram e Blogs via `ddgs` e Vertex AI Search), a deduplicação contra as 4 listas da escalada e a resolução de thumbnails estilo preview do WhatsApp com cache offline.

## Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair vídeos, postagens e artigos de blog candidatos para as escaladas selecionadas usando YouTube Data API v3, Vertex AI Search e o pacote `ddgs` (para Instagram e páginas de blog), sem emitir avisos de depreciação (`RuntimeWarning`) e ignorando URLs que já constem em qualquer uma das 4 listas da escalada (`betas`, `betas_nao_revisados`, `betas_nao_scorados` e `betas_rejeitados`).

#### Scenario: Busca bem sucedida por vídeos
- **WHEN** o coletor recebe uma lista de escaladas identificadas por seu `uid` e metadados geográficos (Nome da Via, Setor, Grupo, Pico, Cidade, Estado)
- **THEN** ele MUST consultar as fontes configuradas (YouTube, Instagram e Blogs) e descartar qualquer candidato cuja URL normalizada já esteja presente em `escalada.betas` ou nas listas `betas_nao_scorados`, `betas_nao_revisados` ou `betas_rejeitados` daquela escalada em `curadoria_betas`.
- **THEN** os novos candidatos encontrados MUST ser estruturados como objetos `CandidatoMidiaBeta` com `midia` (`url`, `titulo`, `fonte`), `snippets` e flags de correspondência preenchidas.

#### Scenario: Scraping de páginas de blog com recorte de janela de contexto
- **WHEN** a busca retorna uma URL classificada como `FonteMidia.BLOG`
- **THEN** o extrator de blogs MUST fazer o download do HTML da página (reutilizando cache em memória por URL durante a sessão de coleta para evitar downloads repetidos do mesmo post).
- **THEN** o extrator MUST validar a presença de vocabulário mínimo de escalada no texto limpo da página e descartar páginas irrelevantes.
- **THEN** o extrator MUST localizar as menções ao nome da escalada no texto do artigo, extrair janelas de contexto de aproximadamente $\pm 300$ caracteres ao redor de cada menção e armazená-las em `CandidatoMidiaBeta.snippets`.

#### Scenario: Busca web via pacote `ddgs` sem RuntimeWarning
- **WHEN** o coletor consulta o buscador web padrão (`_BuscadorDuckDuckGoPadrao`) para localizar postagens do Instagram ou artigos de blog
- **THEN** o sistema MUST utilizar `from ddgs import DDGS` (declarado nos grupos `editor` e `pdf` do `pyproject.toml`) sem disparar `RuntimeWarning` de renomeação do pacote `duckduckgo_search`.

### Requirement: Resolução de Preview Estilo WhatsApp e Cache Offline de Imagens
O sistema SHALL resolver dinamicamente a imagem de pré-visualização (thumbnail) a partir da URL da mídia (`MidiaBeta.url`) sem armazenar `thumbnail_url` no Protobuf, persistindo a imagem baixada em cache local gerenciado pelo provedor de imagens (`ProvedorImagemAresta`) indexado pela URL canônica da mídia para disponibilidade offline.

#### Scenario: Resolução determinística para vídeos do YouTube
- **WHEN** a interface solicita a pré-visualização de uma mídia com `FonteMidia.YOUTUBE`
- **THEN** o provedor MUST extrair o identificador do vídeo a partir da URL (`watch?v=`, `youtu.be/` ou `shorts/`) e recuperar a imagem de `https://i.ytimg.com/vi/<id>/hqdefault.jpg` através do cache persistente offline.

#### Scenario: Resolução via OpenGraph para Blogs e Instagram com fallback visual
- **WHEN** a interface solicita a pré-visualização de uma mídia com `FonteMidia.BLOG` ou `FonteMidia.INSTAGRAM`
- **THEN** o provedor MUST consultar primeiro o cache local em disco indexado pela URL da mídia; caso ausente, MUST requisitar os metadados OpenGraph (`og:image` / `twitter:image`) da página, armazenar os bytes da imagem no cache offline e retornar o `QPixmap`.
- **THEN** caso a página não exponha imagem OpenGraph ou bloqueie a requisição, o sistema MUST exibir um card visual de fallback estilizado de acordo com a `FonteMidia` sem interromper a interface.
