# Tasks

## 1. Omissão $O(1)$ de `ext_metadados_arquivo` e Campos Protobuf `INVISIVEL` no MCP

- [x] 1.1 Escrever testes comportamentais falhando (*Red*) em `editor/mcp/ferramentas_conhecimento_test.py` e `editor/mcp/ferramentas_visao_test.py` validando que `aresta_obter_esquema_proto` e `aresta_obter_arvore` omitem extensões `[aresta.*]` (`ext_metadados_arquivo`) e campos marcados com `INVISIVEL` (`precomputados`, `malha_estrada`, `arquivos_externos`, `ultima_migracao`, `curadoria_betas`, `compilado`, e campos legados `id`, `ids`, `escalada`, `setor`, `grupo`), preservando visíveis `uid`, `alvo_uid` e `pontos_uids`, e verificar a falha com `uv run pytest editor/mcp/ferramentas_conhecimento_test.py editor/mcp/ferramentas_visao_test.py`.
- [x] 1.2 Implementar o mapa pré-computado `_CAMPOS_OCULTOS_MCP` em `editor/mcp/ferramentas_conhecimento.py` e aplicar a filtragem recursiva em `aresta_obter_esquema_proto` e `aresta_obter_arvore` (`editor/mcp/ferramentas_visao.py`), verificando 100% de cobertura comportamental (*Green*) com `uv run pytest editor/mcp/ferramentas_conhecimento_test.py editor/mcp/ferramentas_visao_test.py --cov=editor.mcp.ferramentas_conhecimento --cov=editor.mcp.ferramentas_visao --cov-report=term-missing`.

## 2. Nova Ferramenta MCP `aresta_listar_escaladas` e Atualização de Skills

- [x] 2.1 Escrever testes comportamentais falhando (*Red*) em `editor/mcp/ferramentas_visao_test.py` para `aresta_listar_escaladas` (cobrindo cruzamento com `pontos_de_interesse` e `referencias` em mapas de setor e em `mapas_gerais`, setores dentro de grupos, filtro por `alvo_setor` e filtro por `filtro_nome`) e verificar a falha com `uv run pytest editor/mcp/ferramentas_visao_test.py`.
- [x] 2.2 Implementar `aresta_listar_escaladas` em `editor/mcp/ferramentas_visao.py` e atualizar `.agents/skills/preencher_croqui_yaml/SKILL.md` e `.agents/skills/converter_parte_croqui_para_markdown/SKILL.md`, verificando 100% de cobertura (*Green*) com `uv run pytest editor/mcp/ferramentas_visao_test.py --cov=editor.mcp.ferramentas_visao --cov-report=term-missing`.

## 3. Remoção de Referências de Mapa (`MapasController.remover_referencia` e `aresta_remover_referencia_mapa`)

- [x] 3.1 Escrever testes comportamentais falhando (*Red*) em `editor/controllers/mapas_controller_test.py` e `editor/mcp/ferramentas_comandos_test.py` para `MapasController.remover_referencia` e `aresta_remover_referencia_mapa` (remoção parcial de `pontos_uids` via `CmdAlterarCampo`, remoção total quando `pontos_uids` esvazia ou é omitido via `CmdRemoverRepeated`, reversão via `undo()`) e verificar a falha com `uv run pytest editor/controllers/mapas_controller_test.py editor/mcp/ferramentas_comandos_test.py`.
- [x] 3.2 Implementar `MapasController.remover_referencia` em `editor/controllers/mapas_controller.py` e registrar `aresta_remover_referencia_mapa` em `editor/mcp/ferramentas_comandos.py`, verificando 100% de cobertura (*Green*) com `uv run pytest editor/controllers/mapas_controller_test.py editor/mcp/ferramentas_comandos_test.py --cov=editor.controllers.mapas_controller --cov=editor.mcp.ferramentas_comandos --cov-report=term-missing`.

## 4. Inserção em Lote (`valores`) e `uid_gerado` / `uids_gerados` em `aresta_adicionar_repeated`

- [x] 4.1 Escrever testes comportamentais falhando (*Red*) em `editor/controllers/croqui_controller_test.py` e `editor/mcp/ferramentas_comandos_test.py` validando `adicionar_multiplos_repeated` e `aresta_adicionar_repeated` com `valor` (1 item) e `valores` (múltiplos itens em `CmdMacro`), retornando `uid`, `uid_gerado` e `uids_gerados`, e verificar a falha com `uv run pytest editor/controllers/croqui_controller_test.py editor/mcp/ferramentas_comandos_test.py`.
- [x] 4.2 Implementar `CroquiController.adicionar_multiplos_repeated` em `editor/controllers/croqui_controller.py` e atualizar `aresta_adicionar_repeated` em `editor/mcp/ferramentas_comandos.py`, verificando 100% de cobertura (*Green*) com `uv run pytest editor/controllers/croqui_controller_test.py editor/mcp/ferramentas_comandos_test.py --cov=editor.controllers.croqui_controller --cov=editor.mcp.ferramentas_comandos --cov-report=term-missing`.

## 5. Preservação Opt-In (`preservar_campos_compativeis`) na Troca de `oneof` e Sugestão de Campos Válidos em Erros

- [x] 5.1 Escrever testes comportamentais falhando (*Red*) em `editor/commands/comandos_protobuf_test.py`, `editor/controllers/croqui_controller_test.py` e `editor/mcp/ferramentas_comandos_test.py` validando: (a) a listagem ordenada dos campos válidos na mensagem de `ValueError` quando um campo não existe no `DESCRIPTOR`; e (b) a cópia automática de campos homônimos compatíveis na troca de variante `oneof` quando `preservar_campos_compativeis=True` (mantendo o comportamento padrão quando `False`), verificando a falha com `uv run pytest editor/commands/comandos_protobuf_test.py editor/controllers/croqui_controller_test.py editor/mcp/ferramentas_comandos_test.py`.
- [x] 5.2 Implementar a sugestão de campos válidos em `editor/commands/comandos_protobuf.py` e o parâmetro `preservar_campos_compativeis: bool = False` em `editor/controllers/croqui_controller.py` e `editor/mcp/ferramentas_comandos.py` (`aresta_alterar_campo` e `aresta_alterar_em_lote`), verificando 100% de cobertura (*Green*) com `uv run pytest editor/commands/comandos_protobuf_test.py editor/controllers/croqui_controller_test.py editor/mcp/ferramentas_comandos_test.py --cov=editor.commands.comandos_protobuf --cov=editor.controllers.croqui_controller --cov=editor.mcp.ferramentas_comandos --cov-report=term-missing`.

## 6. Verificação Integrada da Suíte MCP e Qualidade

- [x] 6.1 Executar a suíte completa de testes e cobertura dos módulos afetados (`uv run pytest editor/mcp/ editor/controllers/ editor/commands/`) e validar formatação/linting (`uv run ruff check` e `uv run ruff format --check`).
