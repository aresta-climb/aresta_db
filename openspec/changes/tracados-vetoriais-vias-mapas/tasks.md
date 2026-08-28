# Tarefas de Implementação: Sistema de Traçados Vetoriais e Destaque Dinâmico de Vias em Mapas

## 1. Schema Protobuf e Compilação de Protos

- [ ] 1.1 Atualizar `aresta_api/proto/croqui.proto` com as novas mensagens `LinhaTrajeto`, `DadosConteudoLinha`, `DadosCompiladosLinha`, `NoTrajeto` e `MarcadorCompilado`.
- [ ] 1.2 Estender `PontoDeInteresse` / `ElementoVisual` em `croqui.proto` para incluir o campo `linha` com suporte ao `oneof representacao { DadosConteudoLinha conteudo; DadosCompiladosLinha compilado; }`.
- [ ] 1.3 Executar a compilação dos protos para Python e Dart (`python build.py protos`) e validar a integridade dos testes de validação em `aresta_api/proto_validacao_test.py`.

## 2. Biblioteca Matemática de Spline Catmull-Rom (Library-First & TDD)

- [ ] 2.1 Criar suite de testes unitários em `editor/core/spline_catmull_rom_test.py` cobrindo cálculo da Spline Centripetal Catmull-Rom ($\alpha = 0.5$), conversão para Curvas de Bézier Cúbicas, geração de SVG Path (`d="M ... C ..."`) e tratamento de casos limites (pontos colidentes, nós insuficientes).
- [ ] 2.2 Implementar a biblioteca `editor/core/spline_catmull_rom.py` seguindo TDD rigoroso até atingir 100% de cobertura de testes unitários.
- [ ] 2.3 Escrever testes e atualizar `editor/core/geometrias_poi.py` e `editor/core/geometrias_poi_test.py` para suportar serialização, desserialização e conversão do tipo `linha`.

## 3. Comandos de Histórico e Controller de Mapas (Undo/Redo & TDD)

- [ ] 3.1 Escrever testes unitários em `editor/controllers/mapas_controller_test.py` para criação de linha, remoção de linha, movimentação de nós e alteração de tipos de nó com suporte à pilha `QUndoStack`.
- [ ] 3.2 Implementar classes de `QUndoCommand` e métodos correspondentes no `MapasController` para manipulação segura e reversível de linhas e nós.

## 4. Item Gráfico e Ferramenta de Desenho no Editor de Mapas (Views)

- [ ] 4.1 Criar os itens gráficos `ItemTrajetoLinha` e `AlcaNoLinha` em `editor/views/widget_editor_mapas.py` com renderização da curva suavizada e nós semânticos (Base com tag, Chapeleta, Crux, Parada/Top).
- [ ] 4.2 Implementar a ferramenta visual de Caneta ("Nova Linha") no painel lateral do `WidgetEditorMapas`, com inserção de pontos em tempo real, cancelamento com Esc e finalização com duplo clique ou Enter.
- [ ] 4.3 Adicionar suporte a menu de contexto nos nós para alternar tipos semânticos (`PASSAGEM`, `INICIO_BASE`, `PROTECAO_FIXA`, `TOP_PARADA`, `CRUX`) e inserir/remover nós intermediários.
- [ ] 4.4 Escrever testes de integração e visualização em `editor/views/widget_editor_mapas_test.py` para assegurar o funcionamento da ferramenta de caneta e edição de nós.

## 5. Pipeline de Compilação Offline e Validação Geral

- [ ] 5.1 Atualizar os scripts de compilação de croquis (`scripts/deploy_generated.py` / `scripts/gerar_compilado_md.py`) para pré-calcular o `svg_path` e o `envelope` no `.binarypb` e `compilado.yaml` a partir dos nós em `conteudo`.
- [ ] 5.2 Adicionar testes unitários para a pré-compilação de linhas em `scripts/deploy_generated_test.py`.
- [ ] 5.3 Executar a suite completa de testes e validação do sistema com `python build.py tudo` garantindo 100% de sucesso.
