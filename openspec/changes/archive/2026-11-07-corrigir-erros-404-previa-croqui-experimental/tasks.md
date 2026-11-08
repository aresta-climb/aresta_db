# Tasks

## 1. Resolução Determinística do ID Atual do Croqui no Workspace

- [x] 1.1 [TDD - Red/Green] Adicionar testes de comportamento em `editor/core/workspace_test.py` e implementar `obter_id_croqui_atual()` em `EditorWorkspace`, `ExperimentalWorkspace` e `LocalRepoWorkspace` (`editor/core/workspace.py`), garantindo que em pastas com nome UUID opaco (ex: `41aea39b`) o ID anterior real do croqui seja lido de `compilado/compilado.binarypb` ou `database/croqui.yaml` e que `processar_renomeacao_e_compilacao` NÃO apague `compilado/` quando o ID permanecer igual; verificar com `uv run pytest editor/core/workspace_test.py --cov=editor.core.workspace`.
- [x] 1.2 [TDD - Red/Green] Atualizar `editor/core/croqui_experimental.py` e `editor/core/croqui_experimental_test.py` para garantir que `compilar_croqui` mova e sobreponha artefatos de forma limpa caso diretórios ou arquivos de destino já existam durante a compactação incremental; verificar com `uv run pytest editor/core/croqui_experimental_test.py --cov=editor.core.croqui_experimental`.
- [x] 1.3 [TDD - Red/Green] Atualizar `editor/mcp/ferramentas_ciclo_vida.py` e `editor/mcp/ferramentas_ciclo_vida_test.py` para usar `workspace.obter_id_croqui_atual()` ao determinar `id_atual` no salvamento/compilação via MCP; verificar com `uv run pytest editor/mcp/ferramentas_ciclo_vida_test.py --cov=editor.mcp.ferramentas_ciclo_vida`.

## 2. Fallback Resiliente de Rotas Compactadas no Servidor Celular e Túnel

- [x] 2.1 [TDD - Red/Green] Adicionar teste em `editor/core/tunel_retransmissor_test.py` cobrindo a requisição de `<id_croqui>/imagens/foto.webp` e `<id_croqui>/compilado.binarypb` quando o arquivo está na raiz compactada (`compilado/imagens/foto.webp`) e uma subpasta `<id_croqui>/` existe vazia ou parcialmente populada no disco, e remover a restrição `not caminho_sub.exists()` em `ClienteTunelRetransmissor._ler_arquivo_proxy` (`editor/core/tunel_retransmissor.py`); verificar com `uv run pytest editor/core/tunel_retransmissor_test.py --cov=editor.core.tunel_retransmissor`.
- [x] 2.2 [TDD - Red/Green] Adicionar teste em `editor/core/servidor_celular_test.py` cobrindo o middleware HTTP `reescrever_rotas_compactas` quando a subpasta `<id_croqui>/` existe no disco mas o arquivo solicitado reside na raiz de `compilado/`, e remover a restrição `not caminho_sub.exists()` em `ServidorCelular` (`editor/core/servidor_celular.py`); verificar com `uv run pytest editor/core/servidor_celular_test.py --cov=editor.core.servidor_celular`.

## 3. Guarda de Auto-Salvamento por Inatividade e Identidade em AreaPrincipal

- [x] 3.1 [TDD - Red/Green] Adicionar testes em `editor/legacy_views/area_principal_conexao_test.py` e `editor/legacy_views/area_principal_test.py` validando que: (a) `salvar_croqui` obtém `id_atual` via `workspace.obter_id_croqui_atual()` sem confundir o UUID da pasta com mudança de ID; e (b) o disparo de `MonitorInatividade` (10s) NÃO invoca `salvar_croqui` quando `historico.obter_pilha().isClean()` for `True` e `indice.binarypb` + `catalogo.db` já existirem em `compilado/`, mas invoca normalmente quando houver modificações não salvas (`isClean() == False`); implementar em `editor/legacy_views/area_principal.py` e verificar com `uv run pytest editor/legacy_views/area_principal_conexao_test.py editor/legacy_views/area_principal_test.py`.

## 4. Verificação de Integração Ponta a Ponta

- [x] 4.1 Executar teste de integração e validar 100% de cobertura comportamental nos módulos alterados com `uv run pytest editor/core/workspace_test.py editor/core/croqui_experimental_test.py editor/core/tunel_retransmissor_test.py editor/core/servidor_celular_test.py editor/mcp/ferramentas_ciclo_vida_test.py editor/legacy_views/area_principal_conexao_test.py`.
