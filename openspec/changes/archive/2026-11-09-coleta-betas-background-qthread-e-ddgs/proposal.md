# Proposal

## Why

Ao executar o Wizard **"Coletar Betas..."** em um croqui real com muitas escaladas (como a Gruta da Lapinha, com 132 vias), o diálogo congelou (`Not Responding`) porque o loop de requisições HTTP aos extratores rodava diretamente na thread principal da GUI do Qt e cada candidato adicionado no `CroquiController` disparava uma reconstrução completa dos cards e threads de thumbnail no `PainelCuradoriaBetas`. Além disso, o pacote `duckduckgo_search` emite `RuntimeWarning` a cada busca por ter sido renomeado para `ddgs` e não estava listado nas dependências do grupo `editor` em `pyproject.toml`.

## What Changes

- **Coleta Assíncrona em Background (`WorkerColetaBetas(QThread)`)**: Mover toda a execução de rede dos extratores (`YouTube`, `Instagram`/`DDGS`, `Blog` e `Vertex`) em `DialogoColetarBetas` para uma `QThread` dedicada (`WorkerColetaBetas`), emitindo sinais `progresso_alterado(int, int, str)`, `concluido(list)` e `cancelado(list)` para manter a janela 100% responsiva durante a coleta e permitir cancelamento cooperativo imediato sem travar a UI.
- **Injeção em Lote e Coalescência de Atualização da UI**: Aplicar os candidatos coletados ao final da execução (ou ao cancelar, preservando o progresso parcial já obtido) em uma única transação `CmdMacro("Coletar Betas")` na thread principal, coalescendo as chamadas a `PainelCuradoriaBetas.atualizar_visualizacao()` e garantindo o encerramento limpo das `QThread`s de thumbnail (`WorkerProvedorImagem`) ao destruir cards antigos.
- **Migração de `duckduckgo-search` para `ddgs`**: Atualizar `pyproject.toml` (adicionando `ddgs` aos grupos `editor` e `pdf` e removendo `duckduckgo-search`) e `_BuscadorDuckDuckGoPadrao` em `coleta_de_betas/extratores/blog.py` para importar `from ddgs import DDGS`, eliminando o `RuntimeWarning`.
- **Princípio IX de Engenharia nos `AGENTS.md` (`aresta_db`, `aresta_app` e `fixalog`)**: Adicionar o **Princípio IX — Responsividade Inegociável da UI e Execução Pesada em Background** nos arquivos `AGENTS.md` (e `openspec/config.yaml`) de `aresta_db`, `aresta_app` e `fixalog`, proibindo explicitamente I/O de rede, processamento pesado de imagens/PDF/vídeo/criptografia ou loops em lote na thread principal da UI e exigindo `QThread` (PySide6) ou `Isolate` (Flutter/Dart) com feedback de progresso e cancelamento cooperativo.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida. -->

### Modified Capabilities
- `curation-panel`: Especificar que o Wizard **"Coletar Betas..."** deve executar o scraping de rede em uma `QThread` de background (`WorkerColetaBetas`) sem bloquear o event loop da GUI, permitindo cancelamento imediato e coalescendo a reconstrução dos cards do `PainelCuradoriaBetas`.
- `media-scraping`: Atualizar o requisito do scraper web para utilizar o pacote `ddgs` (`from ddgs import DDGS`) sem emitir avisos de depreciação (`RuntimeWarning`).

## Impact

- `pyproject.toml` e `uv.lock`: Substituição de `duckduckgo-search` por `ddgs` nos grupos `pdf` e `editor`.
- `coleta_de_betas/extratores/blog.py` e `coleta_de_betas/extratores/blog_test.py`: Uso de `ddgs.DDGS` em `_BuscadorDuckDuckGoPadrao`.
- `coleta_de_betas/curadoria/dialogo_coletar_betas.py` e `coleta_de_betas/curadoria/dialogo_coletar_betas_test.py`: Introdução de `WorkerColetaBetas(QThread)` e fluxo assíncrono não-bloqueante no `DialogoColetarBetas`.
- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`: Coalescência de `atualizar_visualizacao` durante mutações em lote e limpeza segura de `WorkerProvedorImagem`.
