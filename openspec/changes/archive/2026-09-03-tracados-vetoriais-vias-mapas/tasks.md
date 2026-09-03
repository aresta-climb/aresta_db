# Tarefas de Implementação: Sistema de Traçados Vetoriais, Cores e Destaque Dinâmico de Vias em Mapas

## 1. Schema Protobuf e Compilação de Protos

- [x] 1.1 Atualizar `aresta_api/proto/croqui.proto` adicionando as novas mensagens `LinhaTrajeto`, `DadosConteudoLinha`, `DadosCompiladosLinha`, `NoTrajeto` e `MarcadorCompilado`, com todas as propriedades em português (`caminho_svg`, `caixa_delimitadora`, `rotulo`, `INICIO_AGACHADO`, etc.).
- [x] 1.2 Estender `PontoDeInteresse` / `ElementoVisual` em `croqui.proto` para incluir o campo `linha` com suporte ao `oneof representacao { DadosConteudoLinha conteudo; DadosCompiladosLinha compilado; }` e o campo `cor` (string hexadecimal `#RRGGBB`).
- [x] 1.3 Executar a compilação dos protos para Python e Dart (`python build.py protos`) e validar a integridade dos testes de validação em `aresta_api/proto_validacao_test.py`.

## 2. Biblioteca Matemática de Spline Catmull-Rom (Library-First & TDD)

- [x] 2.1 (TDD - Teste Primeiro) Criar a suite de testes unitários em `editor/core/spline_catmull_rom_test.py` cobrindo cálculo da Spline Centripetal Catmull-Rom ($\alpha = 0.5$), conversão para Curvas de Bézier Cúbicas, geração de SVG Path (`caminho_svg`), cálculo de caixas delimitadoras e tratamento de casos limites (pontos coincidentes, nós insuficientes).
- [x] 2.2 Implementar a biblioteca pura `editor/core/spline_catmull_rom.py` (sem dependência de GUI) até que todos os testes passem com 100% de cobertura.
- [x] 2.3 (TDD - Teste Primeiro) Atualizar `editor/core/geometrias_poi_test.py` com testes para serialização, desserialização e conversão do tipo `linha` e do campo `cor`, e em seguida atualizar `editor/core/geometrias_poi.py` até atingir 100% de cobertura.

## 3. Comandos de Histórico e Controller de Mapas (Undo/Redo & TDD)

- [x] 3.1 (TDD - Teste Primeiro) Escrever testes unitários em `editor/controllers/mapas_controller_test.py` para criação de linha, remoção de linha, alteração de cor de elementos, movimentação de nós e alteração de tipos de nó com suporte obrigatório à pilha `QUndoStack`.
- [x] 3.2 Implementar as classes de `QUndoCommand` (incluindo `ComandoAlterarCorElemento`) e os métodos no `MapasController` para manipulação segura e reversível de linhas, nós e cores.

## 4. Item Gráfico e Ferramenta de Desenho no Editor de Mapas (Views)

- [x] 4.1 Criar os itens gráficos `ItemTrajetoLinha` e `AlcaNoTrajeto` em `editor/views/widget_editor_mapas.py` com renderização da curva suavizada, cores personalizadas e nós semânticos (Base com tag, Chapeleta, Crux, Parada/Top).
- [x] 4.2 Implementar a ferramenta visual de Caneta ("Nova Linha") no painel lateral do `WidgetEditorMapas`, com inserção de pontos em tempo real, cancelamento com Esc e finalização com duplo clique ou Enter.
- [x] 4.3 Adicionar o seletor visual de cores com a paleta recomendada de alto contraste para rocha (Vermelho, Laranja, Amarelo, Verde Lima, Ciano, Roxo, Branco, Cinza) e opção de cor personalizada.
- [x] 4.4 Adicionar suporte a menu de contexto nos nós para alternar tipos semânticos (`PASSAGEM`, `CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `PROTECAO_FIXA`, `TOP_PARADA`, `CRUX`) e inserir/remover nós intermediários.
- [x] 4.5 Escrever testes de integração e visualização em `editor/views/widget_editor_mapas_test.py` para assegurar o funcionamento da ferramenta de caneta, cores e edição de nós com 100% de cobertura.

## 5. Pipeline de Compilação Offline e Validação Geral

- [x] 5.1 Atualizar os scripts de compilação de croquis (`scripts/deploy_generated.py` / `scripts/gerar_compilado_md.py`) para pré-calcular o `caminho_svg` e a `caixa_delimitadora` no `.binarypb` e `compilado.yaml` a partir dos nós em `conteudo`.
- [x] 5.2 (TDD - Teste Primeiro) Adicionar testes unitários para a pré-compilação de linhas em `scripts/deploy_generated_test.py` e validar execução.
- [x] 5.3 Executar a suite completa de testes e cobertura com `python build.py test` e `python build.py coverage`, garantindo 100% de sucesso e conformidade com `PRINCIPIOS.md`.
