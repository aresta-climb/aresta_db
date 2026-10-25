# Proposal

## Why

Atualmente, quando o usuário adiciona uma nova escalada, setor, grupo ou enfiada na aba de Dados do editor (`WidgetEditorDados`), a mensagem Protobuf correspondente (`Escalada`, `SetorOuGrupo`, `ArquivoSetor`) é instanciada e inserida no `CroquiModel` com o campo `uid` vazio (`""`), só recebendo um NanoID no momento de salvar o croqui em disco (`extrair_arquivos_e_serializar` / `sanear_uids_croqui`). Como resultado, o `IndiceUidsModel` ignora a entidade recém-criada em memória e, se o usuário tentar criar uma referência para ela no Editor de Mapas antes de salvar, a referência é criada com `alvo_uid` vazio e exibida como `"Referência Inválida"`. Garantir a geração automática do `uid` diretamente na construção dos comandos canônicos de mutação (`CmdAdicionarRepeated` e `CmdAlterarCampo`) assegura que toda entidade com `uid` já nasça identificada e indexada no exato instante da adição, mantendo determinismo total em `Undo`/`Redo` e eliminando esquecimentos na camada de interface ou no servidor MCP.

## What Changes

- **Função Pura de Preenchimento Recursivo de UIDs em Mensagens Protobuf (`garantir_uids_em_mensagem`)**:
  - Introduz uma função recursiva e idempotente em `editor/commands/comandos_protobuf.py` (reutilizando `gerar_uid` de `scripts/gerenciar_uids_lib.py`) que inspeciona qualquer `Message` Protobuf (desembrulhando `ReadOnlyProxy` quando necessário) e preenche `msg.uid = gerar_uid()` sempre que o descritor da mensagem possuir o campo `"uid"` e o valor atual estiver vazio/em branco.
  - Percorre apenas os subcampos `TYPE_MESSAGE` efetivamente povoados (itens de listas `repeated`, variantes `oneof` ativas, submensagens singulares presentes via `HasField` e o campo `.conteudo` de envelopes `ONEOF_CONTEUDO` como `ArquivoSetor` e `ArquivoGrupo` quando não apontarem para `caminho` externo).
  - Preserva integralmente qualquer `uid` já preenchido (garantindo determinismo na deserialização de diários e compatibilidade com identificadores explícitos em testes).
- **Geração Automática de UID na Instanciação de `CmdAdicionarRepeated` e `CmdAlterarCampo`**:
  - No `__init__` de `CmdAdicionarRepeated`, executa `garantir_uids_em_mensagem(valor)` sobre o item recebido **antes** de realizar `_copia_segura(valor)`, garantindo que tanto a instância original do chamador quanto a cópia congelada `self.valor` no comando retenham o mesmo `uid` permanente em ciclos de `Undo`/`Redo` e no `diario_pendente.bin`.
  - No `__init__` de `CmdAlterarCampo` (para as modalidades `"oneof"`, `"submensagem"` e `"repeated_item"`), executa `garantir_uids_em_mensagem` sobre a nova mensagem antes de congelar `self.valor_novo` e `self._valor_variante_nova`.
- **Unificação com o Servidor MCP (`editor/mcp/ferramentas_comandos.py`)**:
  - Simplifica `_garantir_uid_em_mensagem` em `editor/mcp/ferramentas_comandos.py` delegando para `garantir_uids_em_mensagem`, mantendo uma única implementação canônica para todo o editor.

## Capabilities

### New Capabilities
*(Nenhuma nova capacidade de topo introduzida.)*

### Modified Capabilities
- `undo-redo-protobuf`: Adiciona o requisito de que `CmdAdicionarRepeated` e `CmdAlterarCampo` garantam automaticamente a geração de `uid` (NanoID 14c) em qualquer mensagem ou subárvore Protobuf recém-introduzida cujo campo `uid` esteja vazio no momento da instanciação do comando, antes de congelar o estado para `Undo`/`Redo` e diário.
- `editor-mapas-referencias`: Atualiza o requisito de criação de referências para garantir que entidades (`Grupo`, `Setor`, `Escalada`) recém-adicionadas na sessão ativa do editor já possuam `uid` indexado no `IndiceUidsModel` e possam ser imediatamente referenciadas em mapas sem necessidade de salvamento prévio em disco.

## Impact

- **Código Afetado**:
  - `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_protobuf_test.py`
  - `editor/mcp/ferramentas_comandos.py` e `editor/mcp/ferramentas_comandos_test.py`
  - `editor/views/widget_editor_dados_test.py` / `editor/views/widget_painel_referencias_test.py` (testes de comportamento integrando adição de entidade na sessão e criação imediata de referência no mapa sem salvar)
- **Performance**:
  - Custo computacional desprezível (microssegundos por comando), pois a varredura recursiva atua exclusivamente sobre a nova mensagem sendo inserida/substituída (tipicamente 1 a 3 nós Protobuf em memória) e ignora campos escalares ou submensagens inativas (`HasField == False`).
- **Compatibilidade**:
  - Zero alterações no schema `croqui.proto`.
  - 100% compatível com diários `diario_pendente.bin` e `diario_salvo.bin` existentes (mensagens deserializadas do diário já possuem seu estado preservado).
