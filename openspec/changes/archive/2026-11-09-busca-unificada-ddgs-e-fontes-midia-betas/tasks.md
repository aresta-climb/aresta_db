# Tasks

## 1. Contrato Protobuf (`aresta_api`)

- [x] 1.1 Expandir `FonteMidia.Enum` em `aresta_api/proto/beta.proto` adicionando `TIKTOK = 4`, `FACEBOOK = 5`, `TWITTER = 6`, `REDDIT = 7` e `OUTRO_UGC = 8`, recompilar os bindings Python/Dart (`aresta_api/proto/generated/beta_pb2.py` e `.pyi`) e verificar com teste de importação dos novos valores do enum.

## 2. Busca Web Unificada, Classificador de Fontes e Prevenção de Rate-Limit

- [x] 2.1 Atualizar `_BuscadorDuckDuckGoPadrao` em `coleta_de_betas/extratores/blog.py` (e testes em `coleta_de_betas/extratores/blog_test.py`) para rotacionar em round-robin entre backends web reais (`yahoo`, `duckduckgo`, `startpage`, `brave`) com `region="br-pt"`, respeitar intervalo mínimo (*pacing*) configurável entre requisições, fazer fallback para o próximo backend em caso de exceção/`202`/`429` e retornar `[]` quando nenhum resultado for encontrado (`No results found`), verificando com `uv run pytest coleta_de_betas/extratores/blog_test.py`.
- [x] 2.2 Implementar `classificar_fonte_url(url: str) -> int | None` e a extração unificada de 1 query aberta por escalada em `coleta_de_betas/extratores/blog.py` (e `coleta_de_betas/extratores/deduplicador.py`), classificando resultados em `YOUTUBE`, `INSTAGRAM`, `TIKTOK`, `FACEBOOK`, `TWITTER`, `REDDIT`, `OUTRO_UGC` e `BLOG`, descartando páginas genéricas de perfil/canal sem post/vídeo, extraindo janelas de contexto de $\pm 300$ chars para páginas textuais e preservando fallback para o snippet do buscador quando o site bloquear download direto mas mencionar a via, verificando com `uv run pytest coleta_de_betas/extratores/blog_test.py coleta_de_betas/extratores/deduplicador_test.py`.
- [x] 2.3 Atualizar `criar_extratores_padrao()` em `coleta_de_betas/curadoria/dialogo_coletar_betas.py` (e `dialogo_coletar_betas_test.py`) para usar por padrão a busca unificada via `ddgs` (1 requisição por escalada cobrindo todas as 8 categorias sem depender de `YOUTUBE_API_KEY` ou `VERTEX_*`), verificando com `uv run pytest coleta_de_betas/curadoria/dialogo_coletar_betas_test.py`.

## 3. Suporte Visual às 8 Categorias na Curadoria e Editor de Dados

- [x] 3.1 Atualizar `obter_pixmap_fallback` em `coleta_de_betas/curadoria/provedor_imagem_aresta.py`, `_rotulo_fonte` em `coleta_de_betas/curadoria/painel_curadoria.py` e `editor/views/widget_editor_dados.py` (com os respectivos testes `_test.py`) para suportar todas as 8 categorias de `FonteMidia.Enum` (`YouTube`, `Instagram`, `Blog`, `TikTok`, `Facebook`, `Twitter`, `Reddit` e `Outro UGC`), verificando com `uv run pytest coleta_de_betas/ editor/views/widget_editor_dados_test.py` e `uv run ruff check coleta_de_betas/ editor/views/widget_editor_dados.py` e `uv run mypy coleta_de_betas/`.
