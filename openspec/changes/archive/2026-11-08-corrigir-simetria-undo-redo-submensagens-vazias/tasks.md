# Tasks

## 1. Poda de Submensagens Singulares Vazias e Resolução Viva em Comandos Protobuf

- [x] 1.1 Escrever testes comportamentais em `editor/commands/comandos_protobuf_test.py` (ciclo *Red*) validando: (a) simetria binária (`SerializeToString(deterministic=True)`) de `Redo` -> `Undo` -> `Redo` ao alterar campo escalar em submensagem singular opcional inicialmente ausente (ex.: `Setor.localizacao_estacionamento.latitude`); (b) preservação de submensagens pertencentes a `oneof` mesmo quando vazias; (c) re-resolução da instância viva em `ComandoEditor._obter_msg()` após `pai.ClearField(...)` mantendo o fallback de `_msg_cache`; e (d) preenchimento de `comando.text()` não vazio em todos os comandos canônicos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`), verificando que os novos testes falham inicialmente com `uv run pytest editor/commands/comandos_protobuf_test.py`.
- [x] 1.2 Implementar em `editor/commands/comandos_protobuf.py` (ciclo *Green* e *Refactor*) a resolução viva prioritária em `ComandoEditor._obter_msg()`, a poda em cascata de submensagens singulares vazias (`containing_oneof is None`) em `CmdAlterarCampo._aplicar_mutacao()` emitindo `dado_alterado` no pai e a definição de `self.setText(...)` nos comandos canônicos, verificando 100% de aprovação e cobertura com `uv run pytest editor/commands/comandos_protobuf_test.py --cov=editor.commands.comandos_protobuf --cov-report=term-missing`.

## 2. Ressincronização de Referências de Submensagens na Interface de Dados

- [x] 2.1 Escrever testes comportamentais em `editor/views/widget_mensagem_coordenada_test.py` e `editor/views/widget_editor_dados_test.py` (ciclo *Red*) validando que editar `latitude` em `localizacao_estacionamento` via `WidgetMensagemCoordenada` / `WidgetFormularioPadrao`, executar `Undo` (que limpa a submensagem no `Setor` pai) e em seguida editar novamente o campo no mesmo formulário em cache funciona sem lançar `ValueError: Mensagem alvo órfã detectada`, verificando a falha inicial com `uv run pytest editor/views/widget_mensagem_coordenada_test.py editor/views/widget_editor_dados_test.py`.
- [x] 2.2 Implementar em `editor/views/widget_mensagem_coordenada.py` e `editor/views/widget_editor_dados.py` (ciclo *Green* e *Refactor*) o vínculo opcional `(msg_pai, campo_pai)` para re-resolução dinâmica da submensagem ativa após `ClearField` no pai, verificando a aprovação e cobertura dos testes com `uv run pytest editor/views/widget_mensagem_coordenada_test.py editor/views/widget_editor_dados_test.py`.

## 3. Validação de Regressão da Issue #85 (Robô Caótico)

- [x] 3.1 Executar a suíte de regressão de caminhos do Robô Caótico sobre a receita da Issue #85 (`crash_seed_4242424257_assertionerror.json`) com `uv run pytest editor/caos/regressao_caminhos_test.py -k "4242424257"` e verificar que a sessão completa executa sem falhas de simetria `Undo/Redo`.
