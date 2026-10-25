# Tasks

## 1. Geração Automática de UIDs nos Comandos Canônicos (`comandos_protobuf.py`)

- [x] 1.1 Escrever testes unitários orientados a comportamento (ciclo *Red* do TDD) em `editor/commands/comandos_protobuf_test.py` validando que `garantir_uids_em_mensagem`, `CmdAdicionarRepeated` e `CmdAlterarCampo` geram `uid` (NanoID 14c) automaticamente para `Escalada`, `SetorOuGrupo` (setor e grupo), `ArquivoSetor`, `Botao`, `PontoDeInteresse` e enfiadas aninhadas sem ativar submensagens singulares vazias (`HasField`), que `IndiceUidsModel` indexa imediatamente a entidade recém-adicionada e que `uid`s pré-existentes ou restaurados em ciclos de `Undo`/`Redo` e deserialização são integralmente preservados (verificar falhas iniciais via `uv run pytest editor/commands/comandos_protobuf_test.py`).
- [x] 1.2 Implementar `garantir_uids_em_mensagem` e integrá-la ao `__init__` de `CmdAdicionarRepeated` e `CmdAlterarCampo` (antes de `_copia_segura`) em `editor/commands/comandos_protobuf.py`, mantendo 100% de cobertura de testes unitários no módulo (`uv run pytest editor/commands/comandos_protobuf_test.py --cov=editor.commands.comandos_protobuf --cov-fail-under=100`).

## 2. Unificação no Servidor MCP e Integração com Referências de Mapa

- [x] 2.1 Atualizar `_garantir_uid_em_mensagem` em `editor/mcp/ferramentas_comandos.py` para reutilizar `garantir_uids_em_mensagem` de `editor/commands/comandos_protobuf.py` e validar 100% de cobertura em `editor/mcp/ferramentas_comandos_test.py` (`uv run pytest editor/mcp/ferramentas_comandos_test.py --cov=editor.mcp.ferramentas_comandos --cov-fail-under=100`).
- [x] 2.2 Adicionar teste de integração comportamental em `editor/views/widget_painel_referencias_test.py` (e/ou `editor/views/widget_editor_dados_test.py`) simulando a adição de novas entidades (`Escalada`, `Setor`, `Grupo`) sem salvar no disco seguida da criação imediata de referência no mapa via `DialogoBuscaReferencia` / `PainelReferencias`, verificando que o card exibe o caminho formatado correto em vez de `"Referência Inválida"` (`uv run pytest editor/views/widget_painel_referencias_test.py editor/views/widget_editor_dados_test.py`).
