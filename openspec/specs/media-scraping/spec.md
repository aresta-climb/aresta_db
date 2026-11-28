# media-scraping Specification

## Purpose
Define a arquitetura dual de extração de mídias de beta (`ExtratorYouTube` via InnerTube JSON + `ExtratorBlog` via `ddgs`), filtragem geográfica ampliada, deduplicação contra as 4 listas da escalada e resolução de thumbnails estilo preview do WhatsApp com cache offline.

## Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair candidatos de mídias de beta através de uma arquitetura dual sem chaves de API pagas: (1) `ExtratorYouTube` dedicado utilizando o endpoint `InnerTube` JSON (`/youtubei/v1/search`) com controle de cadência thread-safe para recuperar vídeos (`watch?v=`) e Shorts (`/shorts/`) sem forçar a palavra `"escalada"` na query; e (2) `ExtratorBlog` utilizando o pacote `ddgs` para exatamente 4 queries (`instagram`, `tiktok`, `facebook` e `geral`) ignorando qualquer resultado do domínio YouTube e extraindo vídeos YouTube/Instagram embutidos no HTML exclusivamente para páginas `FonteMidia.BLOG` já aprovadas nos filtros. Ambos os extratores MUST ignorar sem requisições HTTP escaladas cujo nome seja placeholder genérico (ex.: `Sem nome`, `Projeto 1`, `Via inacabada 2`), higienizar os termos de busca removendo prefixos administrativos do pico (ex.: `Complexo`), enriquecer as queries e o filtro geográfico `menciona_contexto_local` com `Pico.cidade` e `Croqui.nome`, validar matching bidirecional de espaços/typos do nome da via, bloquear domínios agregadores, registrar descartes com prefixo `[Query: <origem> | Auto-filtrado: <motivo>]` em `betas_rejeitados`, e isolar sessões HTTP/2 do `ddgs` por thread com renovação periódica.

#### Scenario: Busca bem sucedida por vídeos
- **WHEN** os extratores (`ExtratorYouTube` e `ExtratorBlog`) recebem uma escalada não placeholder identificada por seu `uid` e metadados geográficos (Nome da Via, Setor, Pico, Cidade e Nome do Croqui)
- **THEN** eles sanitizam o nome da via e do pico (removendo sufixos técnicos como `- Mapa X`, prefixos administrativos como `"Complexo"`, parênteses de projeto e aspas conflitantes), omitem o nome do setor da query textual e enriquecem a busca com `cidade`.
- **THEN** o `ExtratorYouTube` consulta o endpoint `InnerTube` JSON (`POST /youtubei/v1/search`) sem exigir `"escalada"` na query, recuperando vídeos (`watch?v=`) e Shorts (`/shorts/`); o `ExtratorBlog` consulta apenas as 4 queries identificadas (`instagram`, `tiktok`, `facebook` e `geral`) ignorando URLs do domínio YouTube e descartando páginas genéricas de perfil, canal ou login sem post/vídeo específico.
- **THEN** o coletor MUST descartar qualquer URL normalizada (incluindo `/embed/<id>` e `/shorts/<id>` do YouTube e `/reels/` do Instagram) que já esteja presente em `escalada.betas` ou nas listas `betas_nao_scorados`, `betas_nao_revisados` ou `betas_rejeitados` daquela escalada.

#### Scenario: Pulo imediato sem requisições HTTP para nomes placeholder de escalada
- **WHEN** um extrator recebe uma escalada com nome vazio ou placeholder genérico (`"Sem nome 8"`, `"Projeto 1"`, `"Via inacabada 2"`)
- **THEN** ele retorna `([], [])` imediatamente sem disparar nenhuma chamada ao buscador web ou endpoint do YouTube.

#### Scenario: Scraping de páginas de blog com recorte de janela de contexto
- **WHEN** a busca retorna uma URL classificada como `FonteMidia.BLOG`, `FonteMidia.REDDIT` ou qualquer outra categoria de `FonteMidia.Enum`
- **THEN** o `ExtratorBlog` constrói o `CandidatoMidiaBeta` inicialmente a partir de `title` e `body` sem baixar HTML antes da filtragem; exclusivamente após um candidato `FonteMidia.BLOG` passar pelos filtros de precisão, o extrator realiza uma requisição GET leve para extrair vídeos embutidos de YouTube (`watch?v=`, `embed/`, `youtu.be/`, `shorts/`) e Instagram (`p/`, `reel/`), preservando o candidato `BLOG` caso o download HTML falhe ou não contenha embeds.

#### Scenario: Busca web via pacote `ddgs` sem RuntimeWarning
- **WHEN** o adaptador `_BuscadorDuckDuckGoPadrao` executa buscas sucessivas ou concorrentes em múltiplas threads para dezenas ou centenas de escaladas
- **THEN** o sistema MUST isolar uma instância de `DDGS` por thread (`threading.local()`) com User-Agent desktop (`impersonate_os="windows"`) e XPath compatível (`algo-sr | relsrch`), renovando periodicamente a sessão após um número máximo de requisições ou em caso de falha de transporte HTTP/2 para evitar o erro `h2 connection driver error: connection error detected: detected excessive load generating behavior` (`ENHANCE_YOUR_CALM`).
- **THEN** quando o buscador responder sem erro de rede mas sem resultados (`No results found`), o adaptador MUST retornar `[]` imediatamente sem repetir a busca em outros backends em cascata.

#### Scenario: Sanitização da query, matching bidirecional de espaços/typos e blocklist de agregadores
- **WHEN** o coletor avalia os resultados brutos retornados pelos extratores para uma escalada
- **THEN** ele MUST filtrar domínios agregadores de croquis, documentos PDF, trilhas e música (`scribd.com`, `ptdocz.com`, `doceru.com`, `thecrag.com`, `escaladas.com.br`, `wikiloc.com`, `mountainproject.com`, `8a.nu`, `27crags.com`, `thetopo.com`, `tripadvisor`, `wikipedia.org`, `linktr.ee`, `music.youtube.com` e `/reels/audio/`).
- **THEN** para aprovar um candidato rumo a `betas_nao_scorados`, o texto combinado `título + snippet` MUST mencionar o nome da via (com matching simétrico que colapsa espaços em ambos os lados, de modo que `"Karrenglass"` dê match com `"Karren Glass"` e vice-versa, além de tolerância a pequenos typos) **E** corresponder em `menciona_contexto_local` a pelo menos um token significativo (fora `STOPWORDS_PICO`, incluindo `"complexo"`, `"area"`, `"regiao"` e `"nucleo"`) de `nome_pico`, `cidade` ou `nome_croqui`.

#### Scenario: Registro de candidatos auto-filtrados em betas_rejeitados para auditoria
- **WHEN** uma URL válida de post, vídeo ou artigo é descartada durante a coleta por pertencer à blocklist de agregadores ou por não atingir o filtro de precisão (via + contexto local no snippet)
- **THEN** o coletor MUST registrar essa mídia como `MidiaBeta` auto-rejeitada indicando no prefixo do `titulo` tanto a request de origem (`instagram`, `youtube`, `tiktok`, `facebook` ou `geral`) quanto o motivo do filtro (ex.: `"[Query: geral | Auto-filtrado: domínio bloqueado] ..."` ou `"[Query: youtube | Auto-filtrado: sem menção ao pico] ..."`) para que seja inserida em `betas_rejeitados` da escalada, podendo ser reavaliada offline futuramente ou auditada/restaurada na seção **4. Betas Rejeitados**.

### Requirement: Resolução de Preview Estilo WhatsApp e Cache Offline de Imagens
O sistema SHALL resolver dinamicamente a imagem de pré-visualização (thumbnail) a partir da URL da mídia (`MidiaBeta.url`) sem armazenar `thumbnail_url` no Protobuf, mantendo cache em memória RAM (`QPixmap`), cache negativo de URLs sem preview e cache persistente em disco no provedor de imagens (`ProvedorImagemAresta`) indexado pela URL canônica da mídia.

#### Scenario: Resolução determinística para vídeos do YouTube
- **WHEN** a interface solicita a pré-visualização de uma mídia com `FonteMidia.YOUTUBE`
- **THEN** o provedor MUST extrair o identificador do vídeo a partir da URL (`watch?v=`, `youtu.be/` ou `shorts/`) e recuperar a imagem de `https://i.ytimg.com/vi/<id>/hqdefault.jpg` através do cache em RAM ou do cache persistente offline em disco.

#### Scenario: Resolução via OpenGraph para Blogs e Instagram com fallback visual
- **WHEN** a interface solicita a pré-visualização de uma mídia de `INSTAGRAM`, `BLOG`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT` ou `OUTRO_UGC`
- **THEN** o provedor MUST consultar primeiro o cache em memória RAM e o cache local em disco indexados pela URL da mídia; caso ausente e a URL ainda não conste no cache negativo da sessão, MUST requisitar os metadados OpenGraph (`og:image` / `twitter:image`) da página, armazenar os bytes da imagem no cache offline e retornar o `QPixmap`.
- **THEN** caso a página não exponha imagem OpenGraph ou bloqueie a requisição, o provedor MUST registrar a URL no cache negativo em memória para não repetir requisições HTTP nas próximas atualizações visuais e retornar o card visual de fallback estilizado (`obter_pixmap_fallback`).
