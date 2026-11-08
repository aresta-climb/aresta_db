# Proposal

## Why

Ao editar um campo dentro de uma submensagem singular opcional do Protobuf que ainda não estava presente no objeto pai (ex.: `Setor.localizacao_estacionamento`, `Setor.localizacao_escalada`, `Pico.localizacao`, `Grupo.localizacao_*`, `PontoDeInteresse.localizacao`), a execução de `Redo` ativa automaticamente a presença da submensagem no ancestral (`pai.HasField(...) == True`), mas o `Undo` limpa apenas o campo escalar interno (`sub.ClearField(...)`) deixando uma submensagem vazia órfã (`localizacao_estacionamento {}`) no Protobuf. Isso quebra a simetria determinística de Undo/Redo (Issue #85 / Sentry `ARESTA-EDITOR-1B`) e corrompe o hash de estado da `QUndoStack`.

## What Changes

- **Poda automática de submensagens singulares vazias em mutações de campo**: Quando `CmdAlterarCampo` (em `undo()` ou `executar_redo()`) limpar um campo e deixar uma submensagem singular (que não pertença a um `oneof`, ex.: `Coordenada`, `AjusteDeCamera`, `DestinoBotao`) sem nenhum campo preenchido (`len(msg.ListFields()) == 0`), o ancestral deve limpar a presença da submensagem (`pai.ClearField(nome_campo_sub)`), em cascata se necessário, restaurando `pai.HasField(...) == False`.
- **Resolução viva prioritária em `ComandoEditor._obter_msg()`**: Atualizar `ComandoEditor._obter_msg()` para resolver prioritariamente a mensagem alvo na árvore ativa via `navegar_para_alvo(root, self._caminho_msg, indice_uids)` (atualizando `self._msg_cache` com a instância viva atual) e utilizar `self._msg_cache` apenas como fallback caso a navegação não encontre o caminho, evitando que comandos subsequentes de `Redo`/`Undo` operem sobre instâncias C++/`upb` desanexadas após `pai.ClearField(...)`.
- **Ressincronização de referências de submensagens em widgets do formulário (`WidgetMensagemCoordenada` e `WidgetFormularioPadrao`)**: Garantir que widgets vinculados a submensagens singulares inline re-obtenham a instância viva a partir da mensagem pai (`getattr(msg_pai, nome_campo)`) quando a submensagem for limpa e recriada pelo Protobuf (`upb`), prevenindo erros `ValueError: Mensagem alvo órfã detectada` em formulários mantidos em `cached_forms`.
- **Rótulos descritivos (`setText`) nos comandos canônicos**: Definir textos descritivos em `CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem` e `CmdAlterarAnexo` para eliminar descrições vazias (`comando ''`) em diagnósticos de falha e telemetria do Sentry.
- **Receita de regressão da Issue #85**: Incorporar e validar a receita determinística do Robô Caótico (`crash_seed_4242424257_assertionerror.json`) na suíte de regressão de caminhos (`editor/caos/regressao_caminhos_test.py`).

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability necessária -->

### Modified Capabilities
- `undo-redo-protobuf`: Atualiza os requisitos de `Comandos de Edição Protobuf Genericos` e `Resolução Tardia de Mensagens Alvo em Comandos Protobuf` para exigir poda simétrica de submensagens singulares vazias, resolução viva prioritária em `_obter_msg()`, ressincronização de referências de submensagens na UI após `ClearField` no pai e rótulos descritivos (`setText`) nos comandos canônicos.

## Impact

- `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_protobuf_test.py`
- `editor/models/croqui_model.py` e `editor/models/croqui_model_test.py`
- `editor/views/widget_mensagem_coordenada.py` e `editor/views/widget_mensagem_coordenada_test.py`
- `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_dados_test.py`
- `editor/caos/caminhos_regressao/` e `editor/caos/regressao_caminhos_test.py`
