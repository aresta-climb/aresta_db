## 1. Schema Protobuf e Regeneração de Stubs

- [x] 1.1 Adicionar a extensão `bool avancado = 50013;` em `google.protobuf.FieldOptions` no arquivo `aresta_api/proto/croqui.proto` e verificar compilação do proto
- [x] 1.2 Anotar os campos secundários em `ViaEsportiva`, `ViaMovel`, `Boulder`, `ViaMultiplasEnfiadas`, `Highline`, `Setor`, `Pico` e `Croqui` com `[(aresta.avancado) = true]`, assegurando que `nome`, `dificuldade`, `extensao`, `conquistadores`, `data_abertura`, `destaque` e `descricao` permaneçam sem essa opção
- [x] 1.3 Recompilar os stubs Python do Protobuf (`croqui_pb2.py`) e verificar em script de teste que o descriptor expõe a extensão `avancado`

## 2. Testes de Unidade e Integração do Formulário (TDD - Red)

- [x] 2.1 Criar testes unitários em `editor/views/widget_editor_dados_test.py` para a detecção de campos com `(aresta.avancado) = true` e para o cálculo de campos avançados preenchidos vs vazios
- [x] 2.2 Criar testes unitários em `editor/views/widget_editor_dados_test.py` verificando que mensagens sem campos avançados não exibem a seção colapsável de avançados
- [x] 2.3 Criar testes unitários em `editor/views/widget_editor_dados_test.py` verificando que o formulário de uma mensagem com campos avançados vazios é inicializado colapsado e com o rótulo de total de campos
- [x] 2.4 Criar testes unitários em `editor/views/widget_editor_dados_test.py` verificando que o rótulo do expando fechado reflete a contagem de campos preenchidos quando há valores atribuídos
- [x] 2.5 Criar testes de integração em `editor/views/widget_editor_dados_test.py` verificando a alternância de visibilidade (expandir/recolher) e a retenção do estado de expansão na sessão ao navegar entre diferentes nós da árvore
- [x] 2.6 Criar testes de integração em `editor/views/widget_editor_dados_test.py` verificando que alterações em campos dentro da seção avançada são registradas no histórico de Undo/Redo e sincronizam o modelo

## 3. Implementação da UI de Campos Avançados no Editor (Green)

- [x] 3.1 Implementar no `WidgetFormularioPadrao` a rotina de identificação e contagem de campos preenchidos e a segregação de campos em principais e avançados durante `_render_message_fields`
- [x] 3.2 Implementar o contêiner colapsável de campos avançados com botão de alternância estilizado, atualização dinâmica do texto do cabeçalho e exibição/ocultação síncrona dos cards filhos
- [x] 3.3 Implementar a persistência do estado de expansão na sessão do editor no `WidgetFormularioPadrao` / `WidgetEditorDados`, inicializando novos formulários com o estado memorizado
- [x] 3.4 Executar os testes criados no grupo 2 e verificar aprovação completa (Green) com 100% de cobertura das novas linhas

## 4. Verificação de Regressão e Validação do OpenSpec

- [x] 4.1 Executar a suíte completa de testes do editor de dados (`pytest editor/views/widget_editor_dados_test.py editor/views/widget_editor_dados_undo_test.py`) e verificar ausência de regressões
- [x] 4.2 Executar `openspec validate --change editor-campos-avancados-expando` e verificar que todas as especificações e tarefas atendem às regras do OpenSpec
