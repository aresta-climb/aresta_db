## 1. Protobuf e Modelagem de Dados

- [x] 1.1 Adicionar enum `SETA_DIRECIONAL = 12` em `NoTrajeto.TipoNo` em `aresta_api/proto/croqui.proto` e compilar os stubs Python e Dart via `python build.py protos`
- [x] 1.2 Atualizar os dicionários de mapeamento e serialização em `editor/views/widget_editor_mapas.py` (`MAPA_STR_PARA_INT`, `MAPA_NOMES_TIPOS`) e validar via testes unitários em `aresta_api/`

## 2. Editor Desktop - TDD e Renderização de Traçado

- [x] 2.1 (TDD) Escrever testes unitários em `editor/views/widget_editor_mapas_test.py` verificando a cor padrão amarela (`#FFD600`), ausência de borda branca nos badges, fundo preto `#1A1A1A` em repouso, highlight colorido em estado selecionado, cálculo de fonte ampliada e renderização de nó `SETA_DIRECIONAL`
- [x] 2.2 Atualizar a cor padrão para amarelo (`#FFD600`) em `ItemTrajetoLinha`, `MapasController` e na criação de novos traçados
- [x] 2.3 Atualizar o desenho de `AlcaNoTrajeto`: eliminar a borda branca interna, aplicar fundo preto neutro em repouso e cor da via quando selecionada, com casing escuro de 1px e cálculo de fonte para preencher 75-80% do diâmetro
- [x] 2.4 Implementar a renderização visual de `SETA_DIRECIONAL` em `AlcaNoTrajeto` orientada pela tangente da curva e adicionar ação no menu de contexto de tipo de nó com empilhamento em `QUndoCommand`

## 3. Pipeline de Compilação de Croquis

- [x] 3.1 (TDD) Escrever testes unitários em `scripts/preparar_submissao_lib_test.py` garantindo que nós do tipo `SETA_DIRECIONAL` geram `MarcadorCompilado` com `angulo_graus_x100` e tipo correto
- [x] 3.2 Atualizar `scripts/preparar_submissao_lib.py` (`precompilar_linhas_mapas_recursivo`) para pré-calcular e empacotar nós de seta direcional nos arquivos compilados (`.binarypb` e `.yaml`)

## 4. Aplicativo Móvel (Flutter)

- [x] 4.1 (TDD) Escrever testes em `aresta_app/frontend/test/` validando o comportamento de renderização dos marcadores em repouso (preto) e sob seleção (highlight amarelo/cor da via)
- [x] 4.2 Atualizar `MarkerPainter` em `aresta_app/frontend/lib/pages/mapa_interativo.dart`: eliminar a borda branca intermediária, desenhar fundo preto em repouso e cor da via quando `isSelected`, dimensionar fonte para ~80% do diâmetro e renderizar setas direcionais
- [x] 4.3 Atualizar fallback da cor padrão para amarelo (`#FFD600`) em `ConstrutorCaminhoTrajeto` no app Flutter

## 5. Validação Integrada e Cobertura

- [x] 5.1 Executar a suíte de testes com `python build.py test` e verificar cobertura de 100% com `python build.py coverage`
- [x] 5.2 Executar os testes do frontend Flutter garantindo paridade estética 1:1 e regressão zero
