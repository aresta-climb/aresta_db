# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente, `criar_extratores_padrao()` instancia `ExtratorDuckDuckGo` (que faz 1 busca `site:instagram.com` por escalada) e `ExtratorBlog` (que faz 1 busca `-site:youtube.com ...` por escalada), deixando vídeos do YouTube de fora quando `YOUTUBE_API_KEY` não está configurada e dobrando o número de requisições ao `ddgs`. Além disso, o `ddgs` v9 em modo `backend="auto"` dispara múltiplas threads concorrentes (incluindo `wikipedia` e `grokipedia`), levando rapidamente a HTTP `202` no DuckDuckGo e HTTP `429` no Brave.

## Goals / Non-Goals

**Goals:**
- Expandir `FonteMidia.Enum` em `aresta_api/proto/beta.proto` com `TIKTOK = 4`, `FACEBOOK = 5`, `TWITTER = 6`, `REDDIT = 7` e `OUTRO_UGC = 8` (preservando os valores `0..3` existentes).
- Executar **1 única busca aberta por escalada** no `ddgs` (`"<nome_escalada>" <nome_setor> "<nome_pico>" escalada`), classificando e processando cada URL retornada de acordo com sua plataforma (`FonteMidia.Enum`).
- Implementar rotação round-robin entre backends web reais (`yahoo`, `duckduckgo`, `startpage`, `brave`) com `region="br-pt"`, fallback imediato em caso de falha/rate-limit e *pacing* (intervalo mínimo configurável entre requisições) em `_BuscadorDuckDuckGoPadrao`.
- Atualizar a UI (`PainelCuradoria`, `ProvedorImagemAresta` e `widget_editor_dados.py`) para exibir rótulos, cores e opções para todas as 8 categorias de `FonteMidia.Enum`.

**Non-Goals:**
- Remover `ExtratorYouTube` ou `ExtratorVertexSearch` do código — eles permanecem disponíveis para quem quiser injetá-los explicitamente, mas a coleta padrão em `criar_extratores_padrao()` passa a depender exclusivamente da busca unificada via `ddgs`.

## Decisions

### 1. Expansão de `FonteMidia.Enum` em `beta.proto`
- **Decisão**:
  ```protobuf
  message FonteMidia {
    enum Enum {
      INDEFINIDO = 0;
      YOUTUBE = 1;
      INSTAGRAM = 2;
      BLOG = 3;
      TIKTOK = 4;
      FACEBOOK = 5;
      TWITTER = 6;
      REDDIT = 7;
      OUTRO_UGC = 8;
    }
  }
  ```
- **Racional**: Adicionar valores sequenciais (`4..8`) é 100% retrocompatível no Protobuf binário e textual, permitindo distinguir vídeos curtos (`TIKTOK`), redes sociais (`FACEBOOK`, `TWITTER`), fóruns (`REDDIT`), plataformas de escalada/comunidade (`OUTRO_UGC`) e artigos (`BLOG`).

### 2. Classificador de URLs (`classificar_fonte_url`) e Filtro de Páginas de Perfil
- **Decisão**: Criar uma função pura `classificar_fonte_url(url: str) -> int | None` que inspeciona o domínio (`netloc`) e o caminho (`path` / `query`) da URL e retorna o `FonteMidia.Enum` correspondente, ou `None` quando a URL for apenas uma página genérica de perfil/canal sem conteúdo específico de via:
  - `youtube.com` / `youtu.be`: retorna `FonteMidia.YOUTUBE` se tiver vídeo (`watch?v=`, `/shorts/`, `/embed/`, `youtu.be/<id>`); retorna `None` para `/@canal`, `/channel/`, `/c/`, `/user/`.
  - `instagram.com`: retorna `FonteMidia.INSTAGRAM` se o path iniciar com `/p/`, `/reel/`, `/reels/` ou `/tv/`; retorna `None` para perfis raiz (`/usuario/`) ou `/explore/`.
  - `tiktok.com`: retorna `FonteMidia.TIKTOK` se contiver `/video/` ou `vm.tiktok.com/`; retorna `None` para perfis `/@usuario` sem vídeo.
  - `facebook.com` / `fb.watch`: retorna `FonteMidia.FACEBOOK` se contiver `/posts/`, `/videos/`, `/watch`, `/reel/`, `/permalink/`, `story.php` ou `fb.watch/`; retorna `None` para páginas de perfil raiz.
  - `twitter.com` / `x.com`: retorna `FonteMidia.TWITTER` se contiver `/status/`; retorna `None` para perfis raiz.
  - `reddit.com`: retorna `FonteMidia.REDDIT` se contiver `/comments/`.
  - Domínios de UGC de escalada/esporte/vídeo (`thecrag.com`, `mountainproject.com`, `8a.nu`, `wikiloc.com`, `escaladas.com.br`, `summitpost.org`, `ukclimbing.com`, `vimeo.com`, `dailymotion.com`): retorna `FonteMidia.OUTRO_UGC`.
  - Demais domínios HTTP/HTTPS: retorna `FonteMidia.BLOG`.

### 3. Pipeline Unificado de Extração por Escalada (`ExtratorWebUnificado` / `ExtratorBlog`)
- **Decisão**:
  - Para cada escalada, monta-se 1 única query aberta: `f'"{nome_escalada}" {nome_setor} "{nome_pico}" escalada'` (omitindo partes vazias).
  - Para cada item retornado por `buscador.buscar_texto(query, max_resultados=max_resultados)`:
    1. Classifica a URL via `classificar_fonte_url(href)`. Se retornar `None`, ignora.
    2. Se a fonte for de rede social/vídeo (`YOUTUBE`, `INSTAGRAM`, `TIKTOK`, `FACEBOOK`, `TWITTER`): cria imediatamente o `CandidatoMidiaBeta` com `fonte`, `titulo`, `snippets=[body]` e `match_nome_no_snippet = (nome_escalada.lower() in f"{titulo} {body}".lower())`.
    3. Se a fonte for textual/comunidade (`BLOG`, `REDDIT`, `OUTRO_UGC`):
       - Faz download do HTML da página (usando `self._cache_paginas` em memória por URL normalizada).
       - Se o HTML for obtido e contiver vocabulário de escalada + menção ao nome da via, extrai as janelas de $\pm 300$ caracteres ao redor do nome da via para `snippets` e define `match_nome_no_snippet = True`.
       - Caso o site bloqueie scraping HTTP (ex: Reddit/TheCrag retornando 403) ou o corpo não possa ser lido, mas o próprio título/snippet do buscador (`f"{titulo} {body}"`) já mencione explicitamente o nome da escalada (`termo_lower in texto_busca`), preserva o candidato com o snippet do buscador.
  - `criar_extratores_padrao()` em `dialogo_coletar_betas.py` passa a instanciar apenas `[ExtratorBlog()]` (que agora realiza a coleta web aberta unificada de todas as 8 categorias em 1 requisição por via!), eliminando a duplicação de chamadas com `ExtratorDuckDuckGo`.

### 4. Rotação de Backends e Pacing Anti-Rate-Limit em `_BuscadorDuckDuckGoPadrao`
- **Decisão**:
  - `_BuscadorDuckDuckGoPadrao` mantém uma lista de backends web (`BACKENDS_WEB_PADRAO = ("yahoo", "duckduckgo", "startpage", "brave")`), um índice de rotação `_indice_backend` e um `intervalo_minimo_s: float = 0.6` (configurável para `0.0` em testes).
  - Antes de cada requisição real, aguarda o tempo restante desde a última chamada (`time.monotonic()`) para respeitar `intervalo_minimo_s`.
  - Tenta os backends em ordem circular (`region="br-pt"`): assim que um backend retorna resultados não-vazios, avança o ponteiro do round-robin para a próxima via (distribuindo a carga igualmente entre os provedores!). Se um backend lançar exceção (incluindo `DDGSException("No results found.")` ou rate-limit `202`/`429`), tenta o próximo backend da lista; se todos retornarem vazio, retorna `[]` sem levantar erro.

## Risks / Trade-offs

- **[Risk] Alguns portais de UGC (como `thecrag.com` ou `reddit.com`) podem bloquear `requests.get` simples com HTTP 403** → **Mitigação**: Quando o download direto da página falhar ou não retornar HTML legível, o extrator verifica se o próprio título + snippet retornado pelo buscador já contém o nome da escalada; em caso positivo, cria o candidato aproveitando o snippet do buscador.
