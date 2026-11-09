# media-scraping Specification

## Purpose
Define a malha de extratores de mídias de beta (YouTube, Instagram e Blogs via `ddgs` e Vertex AI Search), a deduplicação contra as 4 listas da escalada e a resolução de thumbnails estilo preview do WhatsApp com cache offline.

## Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair candidatos de mídias de beta para as escaladas selecionadas executando uma única busca web aberta por escalada via pacote `ddgs` (com `region="br-pt"`, rotação de backends web e controle de taxa anti-rate-limit, sem exigir `YOUTUBE_API_KEY` ou `VERTEX_*`), classificando cada URL retornada em uma das 8 categorias de `FonteMidia.Enum` (`YOUTUBE`, `INSTAGRAM`, `BLOG`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT`, `OUTRO_UGC`) e ignorando URLs que já constem em qualquer uma das 4 listas da escalada (`betas`, `betas_nao_revisados`, `betas_nao_scorados` e `betas_rejeitados`).

#### Scenario: Busca bem sucedida por vídeos
- **WHEN** o coletor recebe uma escalada identificada por seu `uid` e metadados geográficos (Nome da Via, Setor, Grupo, Pico, Cidade, Estado)
- **THEN** ele MUST executar uma única busca textual aberta no `ddgs` sem restrições `site:` ou `-site:` e classificar cada URL retornada em `YOUTUBE`, `INSTAGRAM`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT`, `OUTRO_UGC` ou `BLOG`.
- **THEN** para links de redes sociais e plataformas de vídeo (`YOUTUBE`, `INSTAGRAM`, `TIKTOK`, `FACEBOOK`, `TWITTER`), o coletor MUST descartar páginas genéricas de perfil/canal sem post ou vídeo específico e construir o `CandidatoMidiaBeta` diretamente a partir do título e snippet retornados pelo buscador.
- **THEN** o coletor MUST descartar qualquer candidato cuja URL normalizada já esteja presente em `escalada.betas` ou nas listas `betas_nao_scorados`, `betas_nao_revisados` ou `betas_rejeitados` daquela escalada em `curadoria_betas`.

#### Scenario: Scraping de páginas de blog com recorte de janela de contexto
- **WHEN** a busca retorna uma URL classificada como `FonteMidia.BLOG`, `FonteMidia.REDDIT` ou `FonteMidia.OUTRO_UGC`
- **THEN** o coletor MUST fazer o download do HTML da página (reutilizando cache em memória por URL durante a sessão de coleta para evitar downloads repetidos da mesma página).
- **THEN** se o texto limpo da página contiver vocabulário de escalada e menções ao nome da via, o coletor MUST extrair janelas de contexto de aproximadamente $\pm 300$ caracteres ao redor de cada menção e armazená-las em `CandidatoMidiaBeta.snippets`; caso o download direto falhe ou o site bloqueie scraping mas o snippet do buscador já mencione o nome da via, o coletor MUST preservar o candidato utilizando o snippet do buscador.

#### Scenario: Busca web via pacote `ddgs` sem RuntimeWarning
- **WHEN** o adaptador `_BuscadorDuckDuckGoPadrao` executa buscas sucessivas para múltiplas escaladas
- **THEN** o sistema MUST utilizar `from ddgs import DDGS` (declarado nos grupos `editor` e `pdf` do `pyproject.toml`) sem disparar `RuntimeWarning` de renomeação do pacote `duckduckgo_search`.
- **THEN** o adaptador MUST consultar `region="br-pt"` rotacionando sequencialmente entre backends de busca web reais (`yahoo`, `duckduckgo`, `startpage`, `brave`) com intervalo mínimo configurável (*pacing*) entre requisições, fazer fallback imediato para o próximo backend em caso de erro/`202`/`429` e retornar `[]` quando nenhum resultado for encontrado (`No results found`).

### Requirement: Resolução de Preview Estilo WhatsApp e Cache Offline de Imagens
O sistema SHALL resolver dinamicamente a imagem de pré-visualização (thumbnail) a partir da URL da mídia (`MidiaBeta.url`) sem armazenar `thumbnail_url` no Protobuf, persistindo a imagem baixada em cache local gerenciado pelo provedor de imagens (`ProvedorImagemAresta`) indexado pela URL canônica da mídia para disponibilidade offline.

#### Scenario: Resolução determinística para vídeos do YouTube
- **WHEN** a interface solicita a pré-visualização de uma mídia com `FonteMidia.YOUTUBE`
- **THEN** o provedor MUST extrair o identificador do vídeo a partir da URL (`watch?v=`, `youtu.be/` ou `shorts/`) e recuperar a imagem de `https://i.ytimg.com/vi/<id>/hqdefault.jpg` através do cache persistente offline.

#### Scenario: Resolução via OpenGraph para Blogs e Instagram com fallback visual
- **WHEN** a interface solicita a pré-visualização de uma mídia de `INSTAGRAM`, `BLOG`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT` ou `OUTRO_UGC`
- **THEN** o provedor MUST consultar primeiro o cache local em disco indexado pela URL da mídia; caso ausente, MUST requisitar os metadados OpenGraph (`og:image` / `twitter:image`) da página, armazenar os bytes da imagem no cache offline e retornar o `QPixmap`.
- **THEN** caso a página não exponha imagem OpenGraph ou bloqueie a requisição, `obter_pixmap_fallback` MUST exibir um card visual de fallback estilizado com cor e rótulo específicos para cada uma das 8 categorias de `FonteMidia.Enum` sem interromper a interface.
