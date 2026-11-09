# Tasks

## 1. Contratos Protobuf (`indice.proto` e `croqui.proto`) — Desacoplado

- [x] 1.1 Adicionar o valor `PROJETO = 38` (ou próximo ID livre) ao enum `GrauBoulder` em `aresta_api/proto/croqui.proto` e o campo `int32 nota_qualidade = 10;` na mensagem `PrecomputadosResumoCroqui` em `aresta_api/proto/indice.proto`, verificando a compilação limpa dos stubs com `uv run python build.py protos -f`.
- [x] 1.2 Atualizar os testes de contrato do `aresta_api` para exercitar a presença de `GrauBoulder.PROJETO` e `PrecomputadosResumoCroqui.nota_qualidade`, verificando que `uv run pytest aresta_api` passa sem erros.

## 2. Motor Determinístico de Avaliação de `nota_qualidade` (`Library-First`) — Desacoplado

- [x] 2.1 Escrever os testes orientados a comportamento em `editor/core/avaliador_nota_qualidade_test.py` (ciclo Red) cobrindo: cálculo aditivo nas 3 etapas (`1000` / `100` / `10` pontos), pontuação parcial linear até a meta de $90\%$, regra de aplicabilidade automática (croqui de 1 setor dispensado de Mapa Geral e croqui 100% Boulder dispensado de extensão/proteções de vias), contabilização de `PROJETO` como grau válido, geração de URIs `ContextoUIPath` nas ações de tarefa e avaliação tanto de objetos Protobuf `Croqui` quanto de dicionários em memória, verificando que os testes falham inicialmente por ausência do módulo.
- [x] 2.2 Implementar a biblioteca `editor/core/avaliador_nota_qualidade.py` (ciclo Green/Refactor) com as dataclasses `AcaoTarefaQualidade`, `TarefaQualidade`, `ResumoEtapaQualidade` e `ResultadoNotaQualidade` e a função pública `avaliar_nota_qualidade_croqui`, verificando que `uv run pytest editor/core/avaliador_nota_qualidade_test.py --cov=editor.core.avaliador_nota_qualidade` atinge 100% de cobertura.

## 3. Pipeline de Compilação (`indice.binarypb`) e Saúde (`STATUS_CROQUIS.md`) — Desacoplado da UI

- [x] 3.1 Atualizar os testes de `scripts/deploy_generated` e `scripts/medir_saude_croquis` (ciclo Red) para exigir o preenchimento de `resumo.precomputados.nota_qualidade` no `indice.binarypb` e `indice.yaml`, bem como a coluna `Nota Qualidade` na tabela gerada em `STATUS_CROQUIS.md`.
- [x] 3.2 Integrar `avaliar_nota_qualidade_croqui` em `scripts/deploy_generated.py` (em `passo_c_gerar_indice` e serialização de `indice.yaml`) e em `scripts/medir_saude_croquis.py`, verificando que os testes unitários e de integração de `scripts/` passam com 100% de cobertura nos trechos modificados.

## 4. Componente Visual Autônomo (`WidgetPainelQualidade`) — Desacoplado da `JanelaPrincipal`

- [x] 4.1 Adicionar o ícone `"painel"` (`fa5s.tachometer-alt`) em `editor/views/estilo.py` e atualizar `editor/views/estilo_test.py`, verificando que `uv run pytest editor/views/estilo_test.py --cov=editor.views.estilo` passa com 100% de cobertura.
- [x] 4.2 Escrever os testes de comportamento isolados da View em `editor/views/widget_painel_qualidade_test.py` (ciclo Red, instanciando `WidgetPainelQualidade` diretamente com `CroquiModel` e `CroquiController` sem usar `JanelaPrincipal`) validando: exibição da `nota_qualidade` total, abertura em cascata automática dos expandos das Etapas 1, 2 e 3 conforme conclusão das etapas, emissão de `foco_requisitado` com a URI `ContextoUIPath` ao clicar nos botões de ação rápida das tarefas, bloqueio do botão de publicar enquanto a Etapa 1 estiver incompleta em rascunhos, alerta para croquis legados já publicados com pendências, e alternância de `publicar_croqui` via comando de Undo/Redo no `CroquiController`.
- [x] 4.3 Implementar `WidgetPainelQualidade` em `editor/views/widget_painel_qualidade.py` (ciclo Green/Refactor) sem mutações diretas no Model e sem tocar em `editor/legacy_views/area_principal.py`, verificando que `uv run pytest editor/views/widget_painel_qualidade_test.py --cov=editor.views.widget_painel_qualidade` atinge 100% de cobertura.

## 5. Acoplamento Final na `JanelaPrincipal` (Somente Após Conclusão dos Grupos 1 a 4)

- [x] 5.1 Acoplar `PaginaPainel` (encapsulando `WidgetPainelQualidade`) como primeira aba (índice `0`) na `JanelaPrincipal` (`editor/legacy_views/area_principal.py`), ajustar os índices de navegação lateral e roteamento `_on_foco_requisitado`, atualizar `editor/README.md` / `editor/views/README.md` e ajustar os testes da janela principal, verificando que todos os testes de `editor/` passam sem regressões.
- [x] 5.2 Executar a validação completa do repositório (`uv run python build.py tudo` e `uv run ruff check .`), verificando que todos os testes passam e que `generated/indice.binarypb`, `generated/indice.yaml` e `STATUS_CROQUIS.md` são atualizados com `nota_qualidade`.
