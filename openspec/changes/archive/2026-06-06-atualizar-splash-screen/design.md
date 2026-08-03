## Context

A `TelaDeAbertura` atual do Editor Aresta usa uma janela sem bordas (`FramelessWindowHint`) e um fundo translúcido para exibição customizada da splash screen enquanto carrega os serviços e aguarda autenticação do GitHub. Por ser frameless, a janela não possui as interações padrão do sistema operacional, tornando-a estática e impossível de mover. Além disso, o ícone atual é genérico, não condizendo com a identidade visual da aplicação móvel associada (`aresta_app`).

## Goals / Non-Goals

**Goals:**
- Alinhar a identidade visual do Editor usando os assets do `aresta_app` (`logo_splash.png` ou `logo_app.png`).
- Tornar a splash screen movível na tela pelos usuários, reimplementando os eventos básicos de arrasto do mouse.

**Non-Goals:**
- Não iremos refatorar o seletor de projetos (`legacy_views/tela_de_carregamento.py`), de acordo com o pedido explícito do usuário.

## Decisions

- **Metodologia de Testes:** O desenvolvimento seguirá Test-Driven Development (TDD). Testes baseados em `QTest` serão adicionados simulando os eventos de `mousePress` e `mouseMove` para atestar a correção do drag-and-drop da tela antes da implementação do código de arrasto em si.
- **Eventos de Mouse:** A `TelaDeAbertura` reimplementará `mousePressEvent` e `mouseMoveEvent`. Salvaremos a posição de referência no clique (`self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()`). No `mouseMoveEvent`, usaremos a variação dessa posição para reposicionar a janela através de `self.move(event.globalPosition().toPoint() - self._drag_pos)`.
- **Recursos Visuais:** Atualizaremos a configuração visual do QLabel responsável por renderizar a imagem, alterando o caminho fonte para os novos recursos copiados para a pasta local `editor/recursos/`.
- **Bundle e Build:** Os novos recursos de imagem serão explicitamente incluídos nos parâmetros de compilação do PyInstaller (via `EditorAresta.spec` ou no script de build), garantindo que sejam empacotados junto com os binários.

## Risks / Trade-offs

- [Risk] Interferência com cliques em botões (ex: botão de copiar código ou abrir GitHub) → Mitigation: O sistema de eventos do Qt processará cliques nos child widgets adequadamente antes de atingirem o background; os botões continuarão funcionais sem que o clique acione o arrasto da janela.
