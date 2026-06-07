## Context

O histórico de comandos `QUndoStack` do `Aresta Editor` hoje é gerido de modo que os comandos protobuf (no `WidgetEditorDados`) recebem uma string de caminho (path) para restaurarem o nó da árvore ativo ao serem desfeitos/refeitos. No entanto, se o usuário trocar de aba global (ex: de Dados para Mapas), o *undo* não trocará automaticamente para a aba "Dados" para mostrar o resultado da ação. Adicionalmente, os comandos do editor de Mapas (ex: `CmdMoverPonto`) não informam seu contexto e a tela não volta para o mapa quando desfeitos.

## Goals / Non-Goals

**Goals:**
- Unificar o formato da string de contexto (como uma URI) para identificar qualquer estado da UI de forma universal.
- Fazer o "shell" principal (`JanelaPrincipal`) responder proativamente a requisições de foco de modo global (alterando o QStackedWidget).
- Criar a classe utilitária `ContextoUIPath` para manipulação idiomática desse caminho em toda a base de código.

**Non-Goals:**
- Acoplar os comandos diretamente à JanelaPrincipal. O acoplamento permanecerá via Inversão de Controle usando eventos (`pyqtSignal`).

## Decisions

- **Formato Universal em String:** Para simplicidade e consistência, a string ditará tanto a página quanto detalhes locais.
  - Ex: `page:dados/node:root/node:Croqui/...` (Aba de dados e respectivo nó).
  - Ex: `page:mapas/file:setor_x.md` (Aba de mapas e o documento).
- **Classe `ContextoUIPath`:** Analisará o path de string original em componentes. Expondo propriedades tipo `.pagina`, `.arquivo`, ou gerando um path local (`path_local_arvore()`).
- **Testes Unitários em TDD:** A classe `ContextoUIPath` será criada inteiramente guiada por testes (TDD), cobrindo 100% dos cenários de parsing, extração e tratamento de rotas globais.
- **Rotas Globais:** `JanelaPrincipal` se conecta ao sinal `foco_requisitado` e direciona as sub-views de acordo com a URI antes da sub-view focar nos detalhes. Os mocks de testes existentes que esperam strings antigas serão atualizados.
- **Sinalização do Mapa:** Como o editor de Mapas não tem `model` (ele mexe num dicionário), vamos usar `GerenciadorHistorico` adicionando nele o sinal `sinal_foco_requisitado`, para o qual a janela também apontará seu listener.

## Risks / Trade-offs

- **Testes Mocks (Risk):** Vários testes de controller ou do adapter da árvore podem injetar paths antigos que não possuem o prefixo de página.
  - *Mitigação:* Atualizar rigorosamente todos os mocks em testes unitários para utilizar o novo padrão de string `page:...`. **Não haverá fallback de compatibilidade legada**, exigindo conformidade estrita da URI na aplicação inteira.
