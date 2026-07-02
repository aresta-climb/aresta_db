## Context

O aplicativo editor é construído utilizando PyQt6. No momento, o fluxo de salvamento do croqui realiza uma série de gravações em disco de forma síncrona, executadas na thread principal. Isso faz com que a janela congele até o término do processo, afetando severamente a experiência do usuário. Em paralelo, a ferramenta de "ajuste de câmera" no mapa cria um componente visual (`ItemCameraOverlay`), porém, por razões a serem investigadas no fluxo (provável `sceneRect` nulo, problema de visibilidade `setVisible` ou `zValue`), ele não aparece na tela. Adicionalmente, quando o usuário entra no modo de linkagem para selecionar POIs, os mesmos continuam com a flag de movimentação ativa, gerando cliques acidentais que alteram suas coordenadas de forma indesejada.

## Goals / Non-Goals

**Goals:**
- Extrair as operações de I/O (`salvar_todas_mudancas` e similares) em `area_principal.py` para uma Worker Thread rodando em background (via `QThreadPool` e `QRunnable`).
- Fornecer feedback visual ao usuário indicando o estado de "Salvando...".
- Corrigir a lógica visual e de injeção na cena do `ItemCameraOverlay` em `widget_editor_mapas.py` para que a caixa roxa de ajuste 9:16 reapareça perfeitamente.
- Bloquear o movimento dos Itens de POI na cena (`ItemInteresse`) apenas durante o modo de linkagem, prevenindo arrastos involuntários.
- Garantir a completude dos testes em 100% nas novas lógicas usando a metodologia TDD.

**Non-Goals:**
- Mudar o modelo assíncrono padrão do PyQt6 para Python genérico `asyncio` no app todo.
- Implementar "Auto-Save" contínuo (o foco aqui é corrigir o travamento explícito do botão salvar manual).

## Decisions

- **Uso de `QRunnable` para salvar**: Será criada (ou atualizada, se já existir `core/worker.py`) uma estrutura de Worker. O modelo de dados a ser salvo deve ser consolidado na thread principal antes de iniciar, garantindo thread-safety. Sinais customizados atualizarão a UI com sucesso ou falha (e restaurarão o estado habilitado dos botões).
- **TDD Rigoroso na UI da Câmera**: Em vez de adivinhar o bug da câmera, implementaremos testes no `widget_editor_mapas_test.py` que validem explicitamente se o overlay foi incluído na cena (`scene() is not None`), se o `rect().isEmpty()` é falso e se está visível (`isVisible()`). A falha no teste guiará a correção do código produtivo.
- **Bloqueio via Flag de Item (`ItemIsMovable`)**: Durante a ativação e desativação do modo de linkagem, iterar sobre os itens de POI na cena e desligar/ligar a flag `QGraphicsItem.GraphicsItemFlag.ItemIsMovable`. Isso resolverá o problema diretamente na API do PyQt de forma elegante e desacoplada.

## Risks / Trade-offs

- **[Risco] Modificação de dados durante o save**: O usuário pode continuar interagindo e alterar dados durante a operação de salvamento demorada, gerando inconsistências no arquivo salvo versus na tela.
  - **Mitigação**: Bloquear temporariamente edições globais ou criar um *snapshot* na memória principal antes de jogar para a thread de disco. O feedback de UI ajudará a desestimular a edição cruzada.
- **[Risco] Testes assíncronos falhos com `pytest-qt`**: O teste pode encerrar antes da thread de salvamento completar.
  - **Mitigação**: Utilizaremos amplamente a diretiva `qtbot.waitUntil()` para garantir que sinais de término foram capturados de forma robusta.
