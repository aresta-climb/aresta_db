## Why

Ao abrir o formulário de edição de entidades do croqui (como vias, setores ou picos), usuários — especialmente iniciantes — são apresentados a dezenas de campos simultaneamente, gerando sobrecarga cognitiva e dificultando o preenchimento rápido das informações essenciais de escalada. 

Esta mudança introduz o princípio de **revelação progressiva** (*progressive disclosure*): os campos fundamentais permanecem visíveis diretamente no formulário, enquanto campos técnicos ou secundários são agrupados sob uma seção colapsável (expando) de "Opções Avançadas", com indicador de dados preenchidos e retenção do estado de expansão durante a sessão do editor.

## What Changes

- **Extensão Protobuf `avancado`**: Introdução da opção de campo `bool avancado = 50013;` em `croqui.proto` para marcar declarativamente quais campos são considerados avançados.
- **Anotação de Campos no Schema**: Marcação dos campos secundários de entidades do croqui (`ViaEsportiva`, `ViaMovel`, `Boulder`, `ViaMultiplasEnfiadas`, `Highline`, `Setor`, `Pico`, `Croqui`) com `(aresta.avancado) = true`. Campos essenciais como `nome`, `dificuldade`, `extensao`, `conquistadores`, `data_abertura`, `destaque` e `descricao` permanecem como campos principais (fora do expando).
- **Agrupamento Dinâmico em Expando**: O `WidgetFormularioPadrao` divide os campos em principais e avançados. Se existirem campos avançados, eles são montados dentro de um contêiner colapsável no final da lista de campos principais.
- **Rótulo Informativo Dinâmico**: O cabeçalho do expando exibe contagem de campos preenchidos quando fechado (ex: `▶ Opções Avançadas (2 preenchidos de 8)` ou `▶ Opções Avançadas (8 campos)`).
- **Persistência de Expansão na Sessão**: A preferência de expansão (aberto ou fechado) é mantida em memória durante a sessão do editor; ao navegar entre vias ou itens na árvore, os novos formulários herdam o estado atual de expansão.
- **Compatibilidade Integral com Undo/Redo e Reatividade**: Os widgets dentro do expando mantêm as propriedades e hierarquia Qt normais, preservando suporte completo à pilha de desfazer/refazer e sincronização com o modelo.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability criada -->

### Modified Capabilities
- `editor-dados-formularios`: Introduz agrupamento e revelação progressiva de campos anotados como avançados no formulário de dados, com indicador de preenchimento e memória de estado na sessão.

## Impact

- **Protobuf (`aresta_api/proto/croqui.proto`)**: Adição da extensão `avancado = 50013` em `google.protobuf.FieldOptions` e anotações nos campos correspondentes; regeneração de stubs Python (`croqui_pb2.py`).
- **Editor UI (`editor/views/widget_editor_dados.py`)**: Atualização de `_render_message_fields` para segregar campos com `avancado = True`, instanciação do contêiner colapsável de avançados e gerenciamento do estado de expansão da sessão.
- **Testes**: Novos testes unitários e de integração em `editor/views/widget_editor_dados_test.py` cobrindo comportamento fechado/aberto, contagem de preenchidos, persistência de navegação e comandos de histórico.
