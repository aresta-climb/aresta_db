## Context

O aplicativo editor é construído utilizando PyQt6. No momento, o fluxo de salvamento do croqui realiza uma série de gravações em disco de forma síncrona, executadas na thread principal. Isso faz com que a janela congele até o término do processo, afetando severamente a experiência do usuário. Em paralelo, a ferramenta de "ajuste de câmera" no mapa cria um componente visual (`ItemCameraOverlay`), porém, por razões a serem investigadas no fluxo (provável `sceneRect` nulo, problema de visibilidade `setVisible` ou `zValue`), ele não aparece na tela. Adicionalmente, quando o usuário entra no modo de linkagem para selecionar POIs, os mesmos continuam com a flag de movimentação ativa, gerando cliques acidentais que alteram suas coordenadas de forma indesejada.

## Goals / Non-Goals

**Goals:**
- Extrair as operações de I/O (`salvar_todas_mudancas` e similares) em `area_principal.py` para uma Worker Thread rodando em background (via `QThreadPool` e `QRunnable`).
- Fornecer feedback visual ao usuário indicando o estado de "Salvando...".
- Corrigir a lógica visual e de injeção na cena do `ItemCameraOverlay` em `widget_editor_mapas.py` para que a caixa roxa de ajuste 9:16 reapareça perfeitamente.
- Bloquear o movimento dos Itens de POI na cena (`ItemInteresse`) apenas durante o modo de linkagem, prevenindo arrastos involuntários.
- Seguir estritamente o `PRINCIPIOS.md`: Utilizar TDD (Red-Green-Refactor), criar testes de integração primeiro, buscar simplicidade (Anti-Abstração) e atingir 100% de unit test coverage para todas as modificações introduzidas. Todas as variáveis e descrições em português.

**Non-Goals:**
- Mudar o modelo assíncrono padrão do PyQt6 para Python genérico `asyncio` no app todo.
- Implementar "Auto-Save" contínuo (o foco aqui é corrigir o travamento explícito do botão salvar manual).

## Decisions

- **Uso de `QRunnable` para salvar**: Será criada (ou atualizada, se já existir `core/worker.py`) uma estrutura de Worker. O modelo de dados a ser salvo deve ser consolidado na thread principal antes de iniciar, garantindo thread-safety. Sinais customizados atualizarão a UI com sucesso ou falha (e restaurarão o estado habilitado dos botões).
- **TDD Rigoroso na UI da Câmera**: Em vez de adivinhar o bug da câmera, implementaremos testes no `widget_editor_mapas_test.py` que validem explicitamente se o overlay foi incluído na cena (`scene() is not None`), se o `rect().isEmpty()` é falso e se está visível (`isVisible()`). A falha no teste guiará a correção do código produtivo.
- **Bloqueio via Flag de Item (`ItemIsMovable`)**: Durante a ativação e desativação do modo de linkagem, iterar sobre os itens de POI na cena e desligar/ligar a flag `QGraphicsItem.GraphicsItemFlag.ItemIsMovable`. Isso resolverá o problema diretamente na API do PyQt de forma elegante e desacoplada.

## Risks / Trade-offs

- **[Risco] Modificação de dados durante o save**: O usuário pode continuar interagindo e alterar dados durante a operação assíncrona, gerando inconsistências ou salvando versões parciais indesejadas se o arquivo for modificado em disco enquanto edita na tela.
  - **Mitigação 1 (Snapshot)**: Para resolver isso de forma elegante, o sistema fará um *snapshot* (cópia imutável na memória principal) do estado exato dos dados a serem salvos **antes** de passá-los para a thread de disco.
  - **Mitigação 2 (Marcação de Estado via Histórico)**: A interface (UI) marcará até qual ponto o dado foi salvo utilizando a posição exata (índice) na pilha de histórico (`QUndoStack`/`QUndoHistory`) no momento do snapshot. Assim, qualquer comando posterior feito pelo usuário avançará a pilha, marcando automaticamente o documento como "necessitando de novo salvamento", garantindo sincronia perfeita com o mecanismo de Undo/Redo do `PRINCIPIOS.md`.
- **[Risco] O usuário tentar fechar o aplicativo enquanto a thread de salvamento opera**: Isso poderia resultar no término prematuro do processo, causando corrupção ou perda de dados do arquivo sendo gravado.
  - **Mitigação**: O `closeEvent` (evento de fechamento) será interceptado de maneira rigorosa. Se houver um salvamento em andamento, a UI será bloqueada com um modal/overlay exibindo "Finalizando salvamento...". O app só fechará automaticamente após o sinal `finalizado` retornar com sucesso. Se retornar com erro (falta de espaço, permissão), o fechamento é **cancelado** (ignorado) e o usuário volta para o editor com o erro exposto.
- **[Risco] Testes assíncronos falhos com `pytest-qt`**: O teste pode encerrar antes da thread de salvamento completar.
  - **Mitigação**: Utilizaremos `qtbot.waitUntil()` rigorosamente. Criaremos **testes de integração primeiro** (PRINCIPIOS.md), e depois desceremos para testes unitários com 100% de coverage.
