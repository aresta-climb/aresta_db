# Proposal

## Why

Atualmente, a coleta de betas dispara múltiplas queries separadas por escalada (`site:instagram.com` e `-site:youtube.com -site:instagram.com ...`) usando a configuração padrão do `ddgs` (`backend="auto"`, `region="us-en"`), o que multiplica o número de requisições HTTP por via, aciona threads paralelas desnecessárias em enciclopédias (`wikipedia`, `grokipedia`), causa bloqueios por rate-limit (`202`/`429`) nos buscadores em croquis grandes e deixa de capturar vídeos do YouTube quando o colaborador não possui uma `YOUTUBE_API_KEY` própria configurada. Fazer **uma única busca aberta por escalada** sem restrição `site:` reduz drasticamente o volume de requisições, evita rate-limit com rotação controlada de backends e exige expandir `FonteMidia.Enum` para classificar adequadamente todas as plataformas retornadas (`YouTube`, `Instagram`, `TikTok`, `Facebook`, `Twitter`, `Reddit`, `OutroUgc` e `Blog`).

## What Changes

- **Expansão de `FonteMidia.Enum` (`beta.proto`)**: Adicionar os valores `TIKTOK = 4`, `FACEBOOK = 5`, `TWITTER = 6`, `REDDIT = 7` e `OUTRO_UGC = 8` ao enum `FonteMidia.Enum` em `aresta_api/proto/beta.proto` (mantendo `INDEFINIDO = 0`, `YOUTUBE = 1`, `INSTAGRAM = 2` e `BLOG = 3`) e recompilar os bindings Python/Dart.
- **Busca Aberta Unificada por Escalada e Classificação Automática por URL**: Unificar a coleta web (`ddgs`) em **1 única requisição aberta por escalada** (`"<nome_escalada>" <nome_setor> "<nome_pico>" escalada`, sem filtros `site:` ou `-site:`), classificando cada URL retornada em uma das 8 categorias de `FonteMidia.Enum`:
  - Redes sociais e plataformas de vídeo (`YOUTUBE`, `INSTAGRAM`, `TIKTOK`, `FACEBOOK`, `TWITTER`): validam se a URL aponta para um conteúdo específico (vídeo/post/reel/status, descartando páginas genéricas de perfil/canal) e utilizam diretamente o título e snippet retornados pelo buscador.
  - Páginas textuais e comunidades (`BLOG`, `REDDIT`, `OUTRO_UGC` como `thecrag.com`, `wikiloc.com`, `escaladas.com.br`, `8a.nu`, `mountainproject.com`, `vimeo.com`): realizam download do HTML (com cache em memória por URL durante a sessão), validam vocabulário de escalada e extraem janelas de contexto de $\pm 300$ caracteres ao redor das menções ao nome da via (com fallback para o snippet do buscador caso o site bloqueie scraping direto mas o snippet já mencione a via).
- **Prevenção de Rate-Limit e Rotação de Backends no `_BuscadorDuckDuckGoPadrao`**:
  - Configurar `region="br-pt"` e substituir `backend="auto"` (que dispara múltiplos motores simultâneos e inclui `wikipedia`/`grokipedia`) por uma rotação sequencial (round-robin + fallback em caso de erro/`202`/`429`) entre os motores web reais (`yahoo`, `duckduckgo`, `startpage`, `brave`).
  - Adicionar controle de cadência (*pacing* configurável entre requisições, padrão em produção e `0.0` nos testes unitários) e tratar `"No results found"` retornando `[]` sem erro.
- **Suporte Visual às 8 Categorias na Curadoria e Editor de Dados**: Atualizar `ProvedorImagemAresta.obter_pixmap_fallback`, `PainelCuradoria` e `widget_editor_dados.py` para exibir rótulos, seletores e badges temáticos para todas as 8 categorias de `FonteMidia.Enum`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida. -->

### Modified Capabilities
- `beta-model`: Expandir `FonteMidia.Enum` em `beta.proto` com `TIKTOK = 4`, `FACEBOOK = 5`, `TWITTER = 6`, `REDDIT = 7` e `OUTRO_UGC = 8`.
- `media-scraping`: Substituir as buscas fragmentadas por domínio por uma busca aberta unificada via `ddgs` (1 requisição por escalada sem exigir `YOUTUBE_API_KEY` ou `VERTEX_*`), com rotação de backends web, *pacing* anti-rate-limit e roteamento/classificação de URLs para as 8 categorias de `FonteMidia.Enum`.
- `curation-panel`: Atualizar os cards de curadoria, thumbnails de fallback e seletores de fonte no Editor para suportar todas as 8 categorias de `FonteMidia.Enum`.

## Impact

- `aresta_api/proto/beta.proto` e bindings gerados em `aresta_api/proto/generated/`.
- `coleta_de_betas/extratores/`: Unificação da busca web/classificador de fontes e resiliência anti-rate-limit em `_BuscadorDuckDuckGoPadrao`, `blog.py`, `duckduckgo.py` e `deduplicador.py`.
- `coleta_de_betas/curadoria/dialogo_coletar_betas.py`, `painel_curadoria.py`, `provedor_imagem_aresta.py` e `editor/views/widget_editor_dados.py`.
