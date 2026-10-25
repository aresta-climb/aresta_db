# Tasks

## 1. Resolução de Alvos em 3 Níveis e Núcleo de Comandos Canônicos

- [x] 1.1 Escrever testes comportamentais (Red) e implementar (Green) o resolvedor híbrido de `alvo` em 3 níveis (`UID` direto -> `<uid_ancestral>.<subcaminho>` -> fallback posicional desde a raiz) em `editor/commands/comandos_protobuf.py` e `editor/models/croqui_model.py`, verificando via `uv run pytest editor/commands/comandos_protobuf_test.py editor/models/croqui_model_test.py` que a resolução e navegação tardia funcionam com 100% de cobertura.
- [x] 1.2 Escrever testes comportamentais (Red) e implementar (Green) o comando unificado `CmdAlterarCampo` guiado por Reflection (`DESCRIPTOR`) em `editor/commands/comandos_protobuf.py`, cobrindo campos escalares primitivos, renomeação de escaladas, variantes e limpeza de `oneof`, submensagens singulares (`TYPE_MESSAGE`), itens indexados de listas (`"<campo>.<indice>"`), captura automática de `valor_antigo`, `mergeWith` por `session_id` e serialização/deserialização, verificando com `uv run pytest editor/commands/comandos_protobuf_test.py --cov=editor.commands.comandos_protobuf`.
- [x] 1.3 Escrever testes comportamentais (Red) e implementar (Green) os comandos `CmdAlterarImagem` (com emissão de `imagem_alterada` e anonimização WebP para telemetria) e `CmdAlterarAnexo` em `editor/commands/comandos_protobuf.py`, verificando adição, substituição, remoção, `undo`/`redo` e serialização com `uv run pytest editor/commands/comandos_protobuf_test.py`.
- [x] 1.4 Atualizar `CmdAdicionarRepeated`, `CmdRemoverRepeated` e `CmdMoverRepeated` em `editor/commands/comandos_protobuf.py` para suportarem integralmente o endereçamento `alvo` em 3 níveis (instância `Message` ou `str` ancorada em `UID`), validando todos os cenários em `editor/commands/comandos_protobuf_test.py`.

## 2. Isolamento dos Comandos Legados para Retrocompatibilidade

- [x] 2.1 Extrair as 12 classes de comandos descontinuadas (`CmdAlterarPrimitivo`, `CmdRenomearEscalada`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdAdicionarMapaArquivo`, `CmdSubstituirImagemMemoria`, `CmdMigrarSetor`) para `editor/commands/comandos_legados.py` e criar a suíte espelhada `editor/commands/comandos_legados_test.py`, verificando 100% de cobertura comportamental e compatibilidade de `deserializar_comando` com `uv run pytest editor/commands/comandos_legados_test.py --cov=editor.commands.comandos_legados --cov-fail-under=100`.
- [x] 2.2 Remover `editor/commands/comandos_mapas.py` e `editor/commands/comandos_mapas_test.py` após migrar `CmdSubstituirImagemMemoria` para `comandos_legados.py`, verificando que nenhum módulo restante importa `comandos_mapas`.


## 3. Refatoração dos Controllers para Comandos Canônicos e `CmdMacro`

- [x] 3.1 Refatorar `editor/controllers/croqui_controller.py` e `editor/controllers/croqui_controller_test.py` para usar exclusivamente `CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo` e `CmdMacro` (incluindo `alterar_campo_imagem`, `inserir_imagem_markdown`, `inserir_botao_markdown`, `alterar_multiplos_repeated_items`, `migrar_setor` e limpeza de imagens órfãs ao remover itens), verificando 100% de cobertura com `uv run pytest editor/controllers/croqui_controller_test.py --cov=editor.controllers.croqui_controller --cov-fail-under=100`.
- [x] 3.2 Refatorar `editor/controllers/mapas_controller.py` e `editor/controllers/mapas_controller_test.py` para usar `CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem` e `CmdMacro` (incluindo `adicionar_mapa_com_arquivo` e substituição de imagem em memória), verificando 100% de cobertura com `uv run pytest editor/controllers/mapas_controller_test.py --cov=editor.controllers.mapas_controller --cov-fail-under=100`.

- [x] 3.3 Atualizar `editor/core/historico.py` (e `editor/core/historico_test.py`) removendo código morto (`CmdRemoverArquivoFisico` e ramificações obsoletas de sinais não assinados), verificando 100% de cobertura com `uv run pytest editor/core/historico_test.py --cov=editor.core.historico --cov-fail-under=100`.

## 4. Atualização do Servidor MCP (`ferramentas_comandos.py` e `resolvedor_alvo.py`)

- [x] 4.1 Atualizar `editor/mcp/ferramentas_comandos.py`, `editor/mcp/resolvedor_alvo.py` e suas respectivas suítes `editor/mcp/ferramentas_comandos_test.py` e `editor/mcp/resolvedor_alvo_test.py` para utilizarem os 7 comandos canônicos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`, `CmdMacro`), mantendo as ferramentas de alto nível (`aresta_migrar_setor`, `aresta_adicionar_mapa_arquivo`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown`, `aresta_vincular_referencia_mapa`) e verificando 100% de cobertura com `uv run pytest editor/mcp/ --cov=editor.mcp --cov-fail-under=100`.

## 5. Guarda Arquitetural AST e Verificação Integrada

- [x] 5.1 Escrever o teste de arquitetura via AST em `editor/arquitetura_mvc_test.py` que proíbe qualquer importação ou uso de `comandos_legados` e de suas 12 classes fora de `deserializar_comando` (em `editor/commands/comandos_protobuf.py`) e de `editor/commands/comandos_legados_test.py`, além de validar que todos os comandos canônicos e legados estão registrados no `deserializar_comando`, verificando com `uv run pytest editor/arquitetura_mvc_test.py`.
- [x] 5.2 Executar a suíte completa de testes e cobertura do editor (`uv run pytest editor/`) para confirmar zero regressões e 100% de cobertura comportamental nos módulos modificados.
