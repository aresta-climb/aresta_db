## Why

Atualmente, qualquer croqui no repositório é incluído no índice compilado e exposto em produção, o que dificulta o desenvolvimento de novos croquis de forma progressiva. Adicionar uma flag `publicar_croqui` (apoiada pela flag de deploy `--producao`) permite criar rascunhos que são compilados e visualizados no ambiente local de desenvolvimento/edição, mas ficam ocultos para os usuários do aplicativo de produção. A migração definirá `publicar_croqui: true` apenas para croquis que atualmente possuem `revisado_manualmente: true`, garantindo que apenas croquis verificados sejam promovidos para produção.

## What Changes

- Adição de um campo booleano `publicar_croqui` à mensagem `Croqui` do Protobuf (`croqui.proto`).
- O script `deploy_generated.py` passa a aceitar a flag `--producao` (ativada por padrão).
- O índice (`indice.binarypb` e `.yaml`) só incluirá croquis onde `publicar_croqui` for `true`, desde que o deploy tenha rodado com `--producao`.
- No ambiente do editor (Editor Aresta), as builds locais rodarão com `--no-producao` para garantir que o croqui em desenvolvimento esteja acessível no preview, independentemente da flag de publicação.
- Criação de um script de migração (one-off) que varre todos os `croqui.yaml` do database e seta `publicar_croqui: true` se possuírem `revisado_manualmente: true`.

## Capabilities

### New Capabilities
- `rascunhos-de-croqui`: Capacidade de manter croquis como rascunhos (invisíveis no índice de produção) enquanto continuam sendo compilados e visualizáveis no ambiente local do editor Aresta.

### Modified Capabilities

## Impact

- `aresta_api/proto/croqui.proto`: Adição de campo `publicar_croqui`.
- `scripts/deploy_generated.py`: Inclusão da lógica de filtro.
- `editor/core/croqui_experimental.py`: Atualização da chamada ao compilador para suportar `--no-producao`.
- `database/*`: Base de dados dos croquis será alterada pontualmente pela migração de dados.
