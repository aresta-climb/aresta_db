## Why

A implementação inicial do `WidgetEditorMapas` tentou introduzir o padrão MVC, mas deixou muito acoplamento na própria camada de View. O widget continuou responsável por ler/escrever arquivos YAML/Markdown cruzes (via `core/mapas_lib.py`) e os comandos do histórico (`CmdMoverPonto`) continuaram encapsulados no mesmo arquivo, manipulando diretamente dicionários de dados ao invés de atuar no `CroquiModel`. Esse acoplamento gera risco de inconsistência, dificulta o teste e quebra os princípios fundamentais da nossa arquitetura. Precisamos realizar um MVC rigoroso.

## What Changes

- **Criação do MapasController**: Centraliza a lógica de interações do mapa (ex: adicionar, mover, deletar pontos) e gerencia as delegações.
- **Movimentação de Comandos**: Extrai `CmdMoverPonto` e outros comandos relacionados para a pasta `commands/comandos_mapas.py`.
- **Limpeza do WidgetEditorMapas**: A View não saberá mais sobre `caminho_pasta` e não lerá/escreverá arquivos; ela reage puramente aos sinais do `CroquiModel` (`repeated_item_alterado`, etc).
- **Rastreamento Granular na View**: A View usará um mapeamento `idx_poi -> QGraphicsItem` e atualizará ativamente seus índices em deleções e adições, para ter performance ótima.
- **Remoção de Arquivos Mortos**: Exclusão definitiva do `core/mapas_lib.py` (a leitura já é feita pelo `carregar_arquivos_externos` do `CroquiModel`).
- **Nova Regra de Teste**: `arquitetura_mvc_test.py` proibirá `QUndoCommand` fora da pasta `commands/` (e de testes).

## Capabilities

### New Capabilities
- Nenhuma. Trata-se de uma refatoração arquitetural (nenhum novo requisito de negócio).

### Modified Capabilities
- Nenhuma alteração de requisitos em nível de usuário. 

## Impact

- `editor/views/widget_editor_mapas.py` será substancialmente limpo.
- `editor/core/mapas_lib.py` será apagado e sua lógica de carregamento é substituída pelo `CroquiModel`.
- Testes de UI e Arquitetura precisarão ser ajustados.
- Nenhuma API externa ou banco de dados existente será quebrado.
