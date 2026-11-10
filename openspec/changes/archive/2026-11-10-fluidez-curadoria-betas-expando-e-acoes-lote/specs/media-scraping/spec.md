## MODIFIED Requirements

### Requirement: APIs de Busca Oficiais e Scrapers
O sistema SHALL extrair candidatos de mídias de beta para as escaladas selecionadas executando buscas direcionadas via pacote `ddgs` (para Instagram, YouTube, TikTok, Facebook e Web/Blogs, usando diretamente `title` e `body` do buscador sem baixar HTML de páginas durante a coleta), higienizando os termos da busca sem incluir o nome técnico do setor, bloqueando domínios agregadores, validando relevância por matching bidirecional de espaços/typos da via + token do pico, encaminhando itens descartados para `betas_rejeitados` para auditoria e isolando sessões HTTP/2 por thread com renovação periódica para evitar bloqueios de carga (`h2 connection driver error`).

#### Scenario: Busca bem sucedida por vídeos
- **WHEN** o coletor recebe uma escalada identificada por seu `uid` e metadados geográficos (Nome da Via, Setor, Pico)
- **THEN** ele MUST sanitizar o nome da via e do pico (removendo sufixos técnicos como `- Mapa X`, parênteses de projeto e aspas conflitantes) e omitir o nome do setor da query textual para não restringir artificialmente os resultados.
- **THEN** ele MUST consultar as 5 queries identificadas (`instagram` com `site:instagram.com`, `youtube` com `site:youtube.com`, `tiktok` com `site:tiktok.com`, `facebook` com `site:facebook.com` e `geral` sem restrição `site:`), classificando cada URL retornada nas categorias de `FonteMidia.Enum` e descartando páginas genéricas de perfil, canal ou login sem post/vídeo específico.
- **THEN** o coletor MUST descartar qualquer URL normalizada que já esteja presente em `escalada.betas` ou nas listas `betas_nao_scorados`, `betas_nao_revisados` ou `betas_rejeitados` daquela escalada.

#### Scenario: Scraping de páginas de blog com recorte de janela de contexto
- **WHEN** a busca retorna uma URL classificada como `FonteMidia.BLOG`, `FonteMidia.REDDIT` ou qualquer outra categoria de `FonteMidia.Enum`
- **THEN** o coletor NÃO MUST realizar download síncrono do HTML da página durante a coleta, construindo o `CandidatoMidiaBeta` diretamente a partir do `title` e `body` (snippet) retornados pelo buscador para manter latência sub-segundo por via.

#### Scenario: Busca web via pacote `ddgs` sem RuntimeWarning
- **WHEN** o adaptador `_BuscadorDuckDuckGoPadrao` executa buscas sucessivas ou concorrentes em múltiplas threads para dezenas ou centenas de escaladas
- **THEN** o sistema MUST isolar uma instância de `DDGS` por thread (`threading.local()`) com User-Agent desktop (`impersonate_os="windows"`) e XPath compatível (`algo-sr | relsrch`), renovando periodicamente a sessão após um número máximo de requisições ou em caso de falha de transporte HTTP/2 para evitar o erro `h2 connection driver error: connection error detected: detected excessive load generating behavior` (`ENHANCE_YOUR_CALM`).
- **THEN** quando o buscador responder sem erro de rede mas sem resultados (`No results found`), o adaptador MUST retornar `[]` imediatamente sem repetir a busca em outros backends em cascata.

#### Scenario: Sanitização da query, matching bidirecional de espaços/typos e blocklist de agregadores
- **WHEN** o coletor avalia os resultados brutos retornados pelo buscador para uma escalada
- **THEN** ele MUST filtrar domínios agregadores de croquis, documentos PDF, trilhas e música (`scribd.com`, `ptdocz.com`, `doceru.com`, `thecrag.com`, `escaladas.com.br`, `wikiloc.com`, `mountainproject.com`, `8a.nu`, `27crags.com`, `thetopo.com`, `tripadvisor`, `wikipedia.org`, `linktr.ee`, `music.youtube.com` e `/reels/audio/`).
- **THEN** para aprovar um candidato rumo a `betas_nao_scorados`, o texto combinado `título + snippet` MUST mencionar o nome da via (com matching simétrico que colapsa espaços em ambos os lados, de modo que `"Karrenglass"` dê match com `"Karren Glass"` e vice-versa, além de tolerância a pequenos typos) **E** pelo menos um token significativo do nome do pico (ex.: `"lapinha"` para `"Gruta da Lapinha"`).

#### Scenario: Registro de candidatos auto-filtrados em betas_rejeitados para auditoria
- **WHEN** uma URL válida de post, vídeo ou artigo é descartada durante a coleta por pertencer à blocklist de agregadores ou por não atingir o filtro de precisão (via + pico no snippet)
- **THEN** o coletor MUST registrar essa mídia como `MidiaBeta` auto-rejeitada indicando no prefixo do `titulo` tanto a request de origem (`instagram`, `youtube`, `tiktok`, `facebook` ou `geral`) quanto o motivo do filtro (ex.: `"[Query: geral | Auto-filtrado: domínio bloqueado] ..."` ou `"[Query: instagram | Auto-filtrado: sem menção à via] ..."`) para que seja inserida em `betas_rejeitados` da escalada e possa ser auditada ou restaurada pelo curador na seção **4. Betas Rejeitados**.

### Requirement: Resolução de Preview Estilo WhatsApp e Cache Offline de Imagens
O sistema SHALL resolver dinamicamente a imagem de pré-visualização (thumbnail) a partir da URL da mídia (`MidiaBeta.url`) sem armazenar `thumbnail_url` no Protobuf, mantendo cache em memória RAM (`QPixmap`), cache negativo de URLs sem preview e cache persistente em disco no provedor de imagens (`ProvedorImagemAresta`) indexado pela URL canônica da mídia.

#### Scenario: Resolução determinística para vídeos do YouTube
- **WHEN** a interface solicita a pré-visualização de uma mídia com `FonteMidia.YOUTUBE`
- **THEN** o provedor MUST extrair o identificador do vídeo a partir da URL (`watch?v=`, `youtu.be/` ou `shorts/`) e recuperar a imagem de `https://i.ytimg.com/vi/<id>/hqdefault.jpg` através do cache em RAM ou do cache persistente offline em disco.

#### Scenario: Resolução via OpenGraph para Blogs e Instagram com fallback visual
- **WHEN** a interface solicita a pré-visualização de uma mídia de `INSTAGRAM`, `BLOG`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT` ou `OUTRO_UGC`
- **THEN** o provedor MUST consultar primeiro o cache em memória RAM e o cache local em disco indexados pela URL da mídia; caso ausente e a URL ainda não conste no cache negativo da sessão, MUST requisitar os metadados OpenGraph (`og:image` / `twitter:image`) da página, armazenar os bytes da imagem no cache offline e retornar o `QPixmap`.
- **THEN** caso a página não exponha imagem OpenGraph ou bloqueie a requisição, o provedor MUST registrar a URL no cache negativo em memória para não repetir requisições HTTP nas próximas atualizações visuais e retornar o card visual de fallback estilizado (`obter_pixmap_fallback`).
