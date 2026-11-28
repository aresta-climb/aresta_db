# Tasks

## 1. Ordem 1.3 e URI `/campo:malha_estrada` no Avaliador e Relatório de Saúde (TDD)

- [x] 1.1 (Red) Atualizar e expandir testes em `editor/core/avaliador_nota_qualidade_test.py` e `scripts/medir_saude_croquis_test.py` validando a ordem da Etapa 1 (`etapa1_malha_estrada_picos` na 3ª posição / `1.3 Malha Estrada`), a URI `/campo:malha_estrada` para `"Gerar mapa de pontos"` e `"Atualizar mapa de pontos"`, e a invalidação segura de cabeçalho legado em `STATUS_CROQUIS.md`; confirmar falha inicial com `uv run pytest editor/core/avaliador_nota_qualidade_test.py scripts/medir_saude_croquis_test.py -n 0`.
- [x] 1.2 (Green/Refactor) Atualizar `editor/core/avaliador_nota_qualidade.py` (`tarefas_etapa1` e ações de `t1_malha_estrada`) e `scripts/medir_saude_croquis.py` (`COLUNAS_TAREFAS_PAINEL` e validação de cabeçalho em `extrair_dados_tabela_markdown`), verificando 100% de cobertura com `uv run pytest editor/core/avaliador_nota_qualidade_test.py scripts/medir_saude_croquis_test.py -n 0 --cov=editor.core.avaliador_nota_qualidade --cov=scripts.medir_saude_croquis --cov-report=term-missing`.

## 2. Scroll Assíncrono Garantido e Foco em `malha_estrada` na Aba Dados (TDD)

- [x] 2.1 (Red) Adicionar testes comportamentais em `editor/views/widget_editor_dados_test.py` cobrindo primeira navegação do Painel para `url_google_maps` (`verticalScrollBar().value() > 0`), navegação via `/campo:malha_estrada` focando `btn_gerar_malha` (`"Gerar Mapa de Pontos"`), primeira exibição do nó raiz `Croqui` focando campo avançado e coalescência de chamadas consecutivas de `focar_campo`; confirmar falha inicial com `uv run pytest editor/views/widget_editor_dados_test.py -k "foco_requisitado" -n 0`.
- [x] 2.2 (Green/Refactor) Refatorar `WidgetFormularioPadrao.load_node` e `focar_campo` em `editor/views/widget_editor_dados.py` (montagem do container antes de `setWidget`, `_posicionar_scroll_no_campo`, `_foco_campo_pendente` coalescido via `QTimer.singleShot(0)` e mapeamento `malha_estrada` → `localizacao`/`btn_gerar_malha`), verificando passagem de `uv run pytest editor/views/widget_editor_dados_test.py -n 0`.

## 3. Verificação Integrada e Linter

- [x] 3.1 Executar suíte completa dos módulos afetados (`editor/views/widget_editor_dados_test.py`, `editor/views/widget_painel_qualidade_test.py`, `editor/core/avaliador_nota_qualidade_test.py`, `scripts/medir_saude_croquis_test.py`) e validar lint/formatação (`uv run ruff check` e `uv run ruff format --check`) sem erros.

## Workflow follow-up

- Sincronizar delta specs com as specs principais e arquivar a change (`openspec-archive-change`).
- Realizar commit e push apenas dos arquivos desta alteração.
