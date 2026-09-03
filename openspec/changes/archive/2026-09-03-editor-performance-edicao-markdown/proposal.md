## Why

A edição de texto Markdown no Editor Aresta apresenta latência severa (vários segundos para registrar poucos caracteres digitados), tornando a experiência de redação de notas, capas e descrições inviável. Esse comportamento decorre de uma cadeia síncrona pesada acionada a cada caractere digitado no loop de eventos principal da interface gráfica:
1. Ausência de temporização de coalescência (*debounce*), processando renderizações completas a cada tecla;
2. Renderização dupla desnecessária por ciclo de eco em `set_conteudo`;
3. Invalidação indevida de cache e releitura massiva de arquivos do disco com recompressão de imagens na telemetria quando comandos de texto são mesclados na pilha de histórico;
4. Reconstrução indevida da lista de mapas da cidade inteira em abas inativas diante de edições textuais;
5. Vazamento cumulativo de filtros de eventos de teclado (`installEventFilter`) a cada atualização de campo.

Essa situação viola o **Princípio II (Library-First)** ao acoplar temporização e regras de coalescência diretamente no interior do componente gráfico de dados, além de violar o **Princípio VI (Simplicidade)** com sobreprocessamento e I/O redundante de disco.

## What Changes

- **Biblioteca Autossuficiente de Coalescência de Digitação (Princípio II - Library-First)**:
  - Criação do módulo desacoplado `editor/core/temporizador_coalescencia.py` (com `temporizador_coalescencia_test.py`), responsável por gerenciar a fila temporizada de atualizações com suporte a reinício de contagem, execução adiada e descarga forçada imediata (*flush*).
- **Integração no Editor Markdown com Prevenção de Duplo Render**:
  - `WidgetEditorMarkdown` passa a utilizar o `TemporizadorCoalescencia` para atualizar a pré-visualização e despachar comandos de alteração para o modelo apenas após pausas naturais de digitação (~250ms) ou perda de foco.
  - Adição de guarda de igualdade em `set_conteudo` para evitar re-renderizações e redimensionamentos repetidos quando o texto recebido for idêntico ao já exibido.
- **Sincronização Incremental no Diário de Comandos (Princípio VII - Comandos do Histórico)**:
  - Aprimoramento de `editor/core/diario.py` e `editor/core/historico.py` para tratar comandos mesclados (`mergeWith`) de forma incremental, atualizando o último comando sem invalidar `_comandos_anonimizados_cache`, eliminando releituras de disco e recompressões de WebP na telemetria a cada batida de tecla.
- **Filtragem Estrita de Sinais no Editor de Mapas**:
  - `WidgetEditorMapas._atualizar_lista_mapas` passa a ignorar sumariamente eventos de alteração de campos puramente textuais (`conteudo`, `descricao`, `notas`), reconstruindo a lista apenas quando a estrutura de mapas for alterada.
- **Instalação Idempotente de Filtros de Evento**:
  - O formulário padronizado passa a registrar o `GlobalUndoRedoFilter` apenas uma única vez por widget, evitando acúmulo na cadeia de eventos do Qt.
- **Conformidade Estrita com os Princípios de Engenharia Aresta**:
  - Todo o código, funções, variáveis, testes e documentação 100% em português brasileiro (**Princípio I**).
  - Testes de integração em primeiro lugar (**Princípio V**).
  - Desenvolvimento orientado a testes TDD Vermelho-Verde-Refatorar (**Princípio IV**).
  - 100% de cobertura de testes unitários (**Princípio III**).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade necessária; trata-se de refinamento de desempenho e robustez das capacidades existentes -->

### Modified Capabilities
- `editor-markdown-imagens`: Requisitos de responsividade, temporização de coalescência na digitação e quebra de ciclos de renderização dupla no `WidgetEditorMarkdown`.
- `editor-diario-recuperacao`: Requisitos de sincronização incremental para comandos mesclados de texto e preservação de cache de telemetria sem reprocessamento redundante em disco.
- `editor-mapas`: Requisito de filtragem estrita de sinais no modelo reativo para evitar reconstruções desnecessárias da lista lateral de mapas.

## Impact

- **Código Afetado**:
  - `editor/core/temporizador_coalescencia.py` [NOVO]: Biblioteca pura/autossuficiente de temporização e coalescência de digitação.
  - `editor/core/temporizador_coalescencia_test.py` [NOVO]: Testes unitários com 100% de cobertura para o temporizador.
  - `editor/core/diario.py` e `editor/core/historico.py`: Sincronização incremental e preservação de cache para comandos mesclados.
  - `editor/core/diario_test.py` e `editor/core/historico_test.py`: Testes de preservação de cache e I/O eficiente.
  - `editor/views/widget_editor_dados.py`: Adoção do temporizador, guarda em `set_conteudo` e instalação única de filtro de eventos.
  - `editor/views/widget_editor_mapas.py`: Filtragem estrita de sinais em `_atualizar_lista_mapas`.
  - `editor/views/campos_customizados_integracao_test.py`: Teste de integração ponta a ponta validando a digitação fluida e preservação de estado no histórico.
- **APIs / Dados**:
  - Nenhuma alteração no esquema Protobuf ou quebra de retrocompatibilidade com o formato do croqui.
