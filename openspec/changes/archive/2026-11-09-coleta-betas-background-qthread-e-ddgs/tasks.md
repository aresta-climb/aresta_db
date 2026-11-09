# Tasks

## 1. Migração de `duckduckgo-search` para `ddgs`

- [x] 1.1 Atualizar `pyproject.toml` (substituindo `"duckduckgo-search"` por `"ddgs"` no grupo `pdf` e adicionando `"ddgs"` ao grupo `editor`), sincronizar o ambiente com `uv sync` e atualizar `_BuscadorDuckDuckGoPadrao` em `coleta_de_betas/extratores/blog.py` e `coleta_de_betas/extratores/blog_test.py` para usar `from ddgs import DDGS` sem emitir `RuntimeWarning`, verificando com `uv run pytest coleta_de_betas/extratores/blog_test.py -W error::RuntimeWarning`.

## 2. Coleta Assíncrona em Background (`WorkerColetaBetas(QThread)`) e Coalescência na UI

- [x] 2.1 Implementar `WorkerColetaBetas(QThread)` em `coleta_de_betas/curadoria/dialogo_coletar_betas.py` (e testes comportamentais em `coleta_de_betas/curadoria/dialogo_coletar_betas_test.py`) para executar o loop de busca e deduplicação em background emitindo sinais `progresso_alterado` e `concluido`, manter a UI responsiva com suporte a cancelamento cooperativo imediato e aplicar os candidatos coletados em um único `CmdMacro("Coletar Betas")` na thread principal, verificando com `uv run pytest coleta_de_betas/curadoria/dialogo_coletar_betas_test.py`.
- [x] 2.2 Atualizar `coleta_de_betas/curadoria/painel_curadoria.py` (e `coleta_de_betas/curadoria/painel_curadoria_test.py`) para coalescer chamadas consecutivas a `_ao_mutar_modelo` (reconstruindo os cards apenas uma vez ao final de uma operação em lote) e encerrar com segurança os workers de imagem (`WorkerProvedorImagem`) ao destruir cards antigos, verificando com `uv run pytest coleta_de_betas/curadoria/painel_curadoria_test.py`.
- [x] 2.3 Executar `uv run ruff check coleta_de_betas/`, `uv run mypy coleta_de_betas/` e `uv run pytest coleta_de_betas/` garantindo 100% de aprovação sem avisos.

## 3. Diretrizes de Engenharia (`AGENTS.md` em `aresta_db`, `aresta_app` e `fixalog`)

- [x] 3.1 Adicionar o **Princípio IX (Responsividade Inegociável da UI e Execução Pesada em Background)** em `AGENTS.md` (e atualizar `openspec/config.yaml` quando presente) nos repositórios `aresta_db`, `aresta_app` e `fixalog`, verificando que os 9 princípios estão documentados de forma coesa em todos os três projetos.
