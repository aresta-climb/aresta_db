# Design: Geração Automática de UIDs nos Comandos Protobuf

## Context

Conforme descrito em `proposal.md`, o Editor Aresta concentra todas as mutações da árvore Protobuf nos comandos canônicos de `editor/commands/comandos_protobuf.py` (`CmdAdicionarRepeated`, `CmdAlterarCampo`, `CmdRemoverRepeated`, `CmdMoverRepeated`). No entanto, quando a interface gráfica (`WidgetEditorDados.executar_adicionar_subelemento` ou botões `+ Adicionar` de cards/listas) instancia uma nova mensagem `Escalada`, `SetorOuGrupo` ou `ArquivoSetor`, o campo `uid` permanece vazio (`""`) até que o usuário salve o croqui em disco.

Durante esse intervalo entre a criação da entidade e o primeiro salvamento:
1. O `IndiceUidsModel` ignora a entidade recém-adicionada porque seus indexadores (`_indexar_grupo`, `_indexar_setor`, `_indexar_escalada`) exigem `uid` não vazio.
2. Qualquer referência criada no Editor de Mapas (`DialogoBuscaReferencia`) para a nova entidade recebe `alvo_uid = ""` e aparece como `"Referência Inválida"` no `PainelReferencias`.
3. Comandos subsequentes na mesma sessão não conseguem endereçar a nova entidade por `UID` (Nível 1/2), caindo em fallback posicional.

## Goals / Non-Goals

**Goals:**
- Garantir que toda mensagem Protobuf introduzida no `CroquiModel` via `CmdAdicionarRepeated` ou `CmdAlterarCampo` possua `uid` preenchido (quando o schema da mensagem ou de suas submensagens contiver o campo `uid`) no exato momento da instanciação do comando.
- Assegurar custo computacional desprezível (apenas na criação do comando e restrito aos nós ativos da mensagem recém-adicionada).
- Garantir determinismo estrito em `Undo` / `Redo` e na persistência em `diario_pendente.bin` / `diario_salvo.bin`.
- Unificar a lógica de preenchimento de `uid` entre os comandos do editor e o servidor MCP (`editor/mcp/ferramentas_comandos.py`).

**Non-Goals:**
- Não alterar o schema `aresta_api/proto/croqui.proto`.
- Não remover o saneamento defensivo de salvamento (`extrair_arquivos_e_serializar` e `sanear_uids_croqui`), que continua existindo como barreira final para arquivos editados manualmente fora do editor.

## Decisions

### 1. Varredura Recursiva Seletiva em `garantir_uids_em_mensagem(msg)`

Em vez de espalhar chamadas a `gerar_uid()` em cada diálogo ou callback da View (`widget_editor_dados.py`), centralizamos uma função recursiva pura `garantir_uids_em_mensagem(msg: Any) -> str` em `editor/commands/comandos_protobuf.py`:

```text
garantir_uids_em_mensagem(msg)
  |
  +-- 1. Se nao for Message Protobuf (ex: int, str, None), retorna "".
  |      (Se for ReadOnlyProxy, desembrulha _obj).
  |
  +-- 2. Se "uid" in msg.DESCRIPTOR.fields_by_name:
  |      Se not getattr(msg, "uid", "").strip():
  |          msg.uid = gerar_uid()
  |
  +-- 3. Caso envelope ONEOF_CONTEUDO (ArquivoSetor / ArquivoGrupo):
  |      Se msg.DESCRIPTOR.name in ("ArquivoSetor", "ArquivoGrupo")
  |         e msg.WhichOneof("arquivo") != "caminho":
  |          garantir_uids_em_mensagem(msg.conteudo)
  |
  +-- 4. Para cada field TYPE_MESSAGE em msg.DESCRIPTOR.fields:
         - Se repeated: itera sobre getattr(msg, field.name)
         - Se em oneof: visita apenas se WhichOneof(oneof) == field.name
         - Se singular: visita apenas se msg.HasField(field.name)
```

**Por que essa varredura é extremamente barata (microssegundos)?**
- Ela **não** varre o croqui inteiro; ela inspeciona **apenas o novo item** passado ao comando (`valor` em `CmdAdicionarRepeated` ou `valor_novo` em `CmdAlterarCampo`).
- Ao adicionar uma `Escalada`, `Botao` ou `PontoDeInteresse`, a mensagem tem profundidade 1 (e 0 submensagens `repeated` preenchidas): são apenas ~5 instruções em Python.
- Ao adicionar um `SetorOuGrupo`, a árvore tem 3 nós (`SetorOuGrupo` -> `ArquivoSetor` -> `Setor`).
- Submensagens singulares vazias (`localizacao`, `precomputados`, `ajuste_de_camera`) são ignoradas em $O(1)$ por `msg.HasField(field.name)` sem sequer instanciá-las no Protobuf.

### 2. Momento da Execução: No `__init__` do Comando, Antes de `_copia_segura`

Em `CmdAdicionarRepeated.__init__`:
```python
garantir_uids_em_mensagem(valor)
self.valor: Any = _copia_segura(valor)
```
E em `CmdAlterarCampo.__init__`:
```python
if isinstance(valor_novo, tuple) and len(valor_novo) == 2:
    garantir_uids_em_mensagem(valor_novo[1])
else:
    garantir_uids_em_mensagem(valor_novo)
```
(Aplicando também a `self._valor_variante_nova` quando `modalidade == "oneof"`).

**Racional:**
1. **Mutação in-place da referência do chamador**: Se o chamador criou `val = croqui_pb2.Escalada()` e chamou `controller.adicionar_repeated(setor, "escaladas", idx, val)`, `val.uid` passa a estar preenchido imediatamente após a criação do comando.
2. **Congelamento imutável para `Undo`/`Redo`**: Como `self.valor = _copia_segura(valor)` ocorre logo em seguida, `self.valor` guarda o `uid` gerado. Quando o usuário executa `Undo` e depois `Redo`, `executar_redo()` reinsere `self.valor` com o **mesmo `uid`**.
3. **Preservação de `uid` pré-existente**: Como a condição é `if not getattr(msg, "uid", "").strip():`, qualquer mensagem que já possua `uid` (por exemplo, ao deserializar um comando do `diario_pendente.bin` via `CmdAdicionarRepeated.deserializar` ou em testes unitários que passam `uid="esc_1"`) mantém seu identificador original intacto.

## Risks / Trade-offs

- **[Risco] Ativação indesejada de submensagens vazias no Protobuf durante a varredura** → **Mitigação**: Em Protobuf Python, acessar `getattr(msg, campo_submensagem)` em um campo singular cria uma submensagem vazia como efeito colateral (`HasField` passa a ser `True`). Por isso, no passo 4 da varredura, verificamos estritamente `msg.WhichOneof(...) == field.name` (para campos `oneof`) e `msg.HasField(field.name)` (para campos singulares fora de `oneof`) **antes** de chamar `getattr(msg, field.name)`. A única exceção deliberada é `msg.conteudo` em `ArquivoSetor` e `ArquivoGrupo` quando `WhichOneof("arquivo") != "caminho"`, pois em memória no editor um setor ou grupo recém-criado sempre reside em `.conteudo`.
- **[Risco] Geração de novo UID a cada Redo quebrando referências criadas depois** → **Mitigação**: A geração ocorre exclusivamente no `__init__` (quando o `uid` está vazio), e nunca dentro de `executar_redo()` se `self.valor` já possui `uid`.
