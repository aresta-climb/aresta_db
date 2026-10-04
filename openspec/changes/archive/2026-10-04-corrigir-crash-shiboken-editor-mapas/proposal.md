# Proposta: Cancelamento Seguro de Modos Interativos e Correção de Ciclo de Vida no Editor de Mapas

## Why

Durante a utilização do Editor de Mapas, se o usuário iniciar um modo interativo de desenho (como polígono ou nova rota) e subsequentemente trocar de mapa, recarregar a imagem ou acionar ações que invoquem `cena.clear()` ou recriem a cena gráfica, os itens gráficos temporários associados à cena anterior (`QGraphicsPathItem`, `QGraphicsEllipseItem`, etc.) são destruídos fisicamente pelo motor C++ do Qt. Como as variáveis de controle (`modo_desenho`, `modo_nova_rota`) permaneciam ativas e mantinham referências a esses objetos destruídos, o próximo clique do mouse disparava um erro fatal no Shiboken (`RuntimeError: libshiboken: Internal C++ object already deleted`), reportado via Sentry.

Esta proposta resolve a fragilidade cancelando proativamente quaisquer modos interativos e limpando referências temporárias antes de qualquer recarregamento, descarregamento ou substituição da cena gráfica, além de adotar validações defensivas com `shiboken6.isValid()` para impedir acessos a ponteiros destruídos.

## What Changes

- **Cancelamento Automático de Modos Interativos**:
  - Implementar método centralizado de cancelamento seguro de estados transitórios (`cancelar_modos_interativos`) que encerra e limpa `modo_desenho`, `modo_nova_rota`, `modo_conversao`, `modo_camera` e `modo_linkagem`.
  - Invocar esse cancelamento em `set_mapa_atual`, `descarregar_mapa`, antes de `cena.clear()` em `_renderizar_mapa`, e ao detectar invalidação do mapa ativo.
- **Defensividade no Descarte de Itens Gráficos Temporários**:
  - Garantir que `cancelar_modo_desenho()` e `cancelar_modo_nova_rota()` utilizem `shiboken6.isValid(item)` antes de chamar `cena.removeItem(item)` ou acessar propriedades do item, evitando exceções secundárias caso a cena já tenha sido limpa.
- **Guarda de Integridade nos Callbacks de Eventos de Desenho**:
  - Em `adicionar_ponto_desenho`, `adicionar_ponto_nova_rota` e `mouseMoveEvent` (snap/mira), verificar se o item temporário é válido em C++ e pertence à cena ativa antes de mutá-lo (`setPath`, `setPos`); caso inválido, reiniciar o item ou abortar a ação com segurança sem propagar `RuntimeError`.
- **Cobertura de Testes Automatizados**:
  - Testes unitários com `pytest-qt` simulando cliques de desenho após trocas de mapas, recargas de imagem, `clear()` de cena e comandos de undo/redo para blindar regressões.

## Capabilities

### Modified Capabilities
- `editor-mapas`: Adicionar requisito de cancelamento seguro e sincronização do ciclo de vida de modos interativos de desenho e anotação perante trocas de mapas, recarregamentos de cena e descarte de recursos gráficos.

## Impact

- **Código Afetado**: `editor/views/widget_editor_mapas.py` e sua respectiva suíte de testes `editor/views/widget_editor_mapas_test.py`.
- **APIs/Contratos**: Nenhuma alteração de schema Protobuf ou API externa; mudança estritamente voltada à estabilidade e robustez de ciclo de vida da interface gráfica PySide6.
