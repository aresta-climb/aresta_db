# Tasks

## 1. Suporte ao Sufixo `/campo:<nome_campo>` no `ContextoUIPath`

- [x] 1.1 Escrever testes de comportamento em `editor/core/contexto_test.py` validando a extração de `campo_alvo` e a preservação de `caminho_local_arvore` quando a URI contém `/campo:<nome_campo>` (e `None` quando ausente), e implementar o parsing em `editor/core/contexto.py` mantendo 100% de cobertura (`uv run pytest editor/core/contexto_test.py --cov=editor.core.contexto --cov-report=term-missing`).

## 2. Scroll, Foco e Auto-Expansão de Opções Avançadas no `WidgetEditorDados`

- [x] 2.1 Escrever testes de comportamento em `editor/views/widget_editor_dados_test.py` cobrindo `focar_campo` e `_on_foco_requisitado` com `/campo:<nome_campo>` (scroll e foco em campo principal, auto-expansão de `WidgetSecaoAvancada` quando o campo alvo é avançado, foco quando o nó já está selecionado na árvore e expansão do ancestral ao navegar para `.../expando:escaladas/item:0/campo:destaque`).
- [x] 2.2 Implementar `focar_campo(nome_campo)` em `WidgetFormularioPadrao` e atualizar `_on_foco_requisitado` em `WidgetEditorDados` (`editor/views/widget_editor_dados.py`), verificando a passagem integral de `uv run pytest editor/views/widget_editor_dados_test.py`.

## 3. Revisão dos Rótulos Diretos e URIs das 22 Tarefas no Avaliador e no Painel

- [x] 3.1 Atualizar e adicionar testes em `editor/core/avaliador_nota_qualidade_test.py` validando o desmembramento de ações por campo pendente com sufixo `/campo:<nome_campo>`, a omissão do nome do pico em croquis com 1 único pico vs. inclusão em múltiplos picos, e a navegação direta para a primeira escalada do setor na tarefa 2.5 (`.../expando:escaladas/item:0/campo:destaque`).
- [x] 3.2 Atualizar `avaliar_nota_qualidade_croqui` em `editor/core/avaliador_nota_qualidade.py` com os novos rótulos imperativos diretos e URIs `/campo:<nome_campo>` em todas as 22 tarefas das Etapas 1, 2 e 3, garantindo 100% de cobertura (`uv run pytest editor/core/avaliador_nota_qualidade_test.py --cov=editor.core.avaliador_nota_qualidade --cov-report=term-missing`).
- [x] 3.3 Atualizar os testes em `editor/views/widget_painel_qualidade_test.py` e remover o prefixo `"Ir para: "` de `CardTarefaQualidade.atualizar_tarefa` em `editor/views/widget_painel_qualidade.py`, verificando 100% de cobertura (`uv run pytest editor/views/widget_painel_qualidade_test.py --cov=editor.views.widget_painel_qualidade --cov-report=term-missing`).

## 4. Verificação Integrada e Qualidade

- [x] 4.1 Executar a validação das especificações OpenSpec (`openspec validate acoes-diretas-painel-qualidade`), o linter/formatador (`uv run ruff check` e `uv run ruff format --check`) e a suíte de testes dos módulos afetados para confirmar zero regressões.
