# Design

## Context

Veja `proposal.md` para a motivação e a descrição da Issue #85 (Sentry `ARESTA-EDITOR-1B`).

No runtime Python/C++ (`upb`) do Protobuf:
1. Acessar uma submensagem singular opcional ausente via `getattr(pai, nome_campo)` retorna uma instância de mensagem vinculada ao pai sem ativar `pai.HasField(nome_campo)`.
2. Atribuir qualquer campo escalar dentro dessa submensagem ativa automaticamente `pai.HasField(nome_campo) == True`.
3. Chamar `sub_msg.ClearField(campo_interno)` remove o campo escalar interno, mas **não** desativa `pai.HasField(nome_campo)`, deixando uma submensagem vazia (`sub_msg.ListFields() == []`) serializada no binário do Protobuf.
4. Chamar `pai.ClearField(nome_campo)` restaura `pai.HasField(nome_campo) == False`, mas **desanexa** a instância Python/C++ antiga `sub_msg` do objeto `pai`. Qualquer código que retenha uma referência direta à instância antiga (`_msg_cache` em `ComandoEditor` ou `self.msg` em `WidgetMensagemCoordenada` / widgets de submensagem em `WidgetFormularioPadrao`) passará a apontar para um objeto órfão desconectado da árvore do `CroquiModel`.

## Goals / Non-Goals

**Goals:**
- Garantir simetria binária determinística (`SerializeToString(deterministic=True)`) em ciclos de `Redo` e `Undo` para edições em submensagens singulares opcionais.
- Garantir que `ComandoEditor._obter_msg()` e os widgets de formulário (`WidgetMensagemCoordenada` e submensagens inline em `WidgetFormularioPadrao`) nunca fiquem presos a referências `upb` desanexadas após `pai.ClearField(...)`.
- Fornecer rótulos textuais informativos (`setText`) em todos os comandos canônicos de `editor/commands/comandos_protobuf.py`.

**Non-Goals:**
- Alterar o schema `.proto` em `aresta_api` ou o formato de persistência dos diários (`diario_pendente.bin` e `diario_salvo.bin`).
- Podar submensagens que façam parte de um `oneof` (cujo ciclo de vida já é gerenciado explicitamente pela modalidade `"oneof"` de `CmdAlterarCampo` guardando `_var_antiga` e `_valor_variante_antiga`).

## Decisions

### 1. Poda em cascata de submensagens singulares vazias após mutação em `CmdAlterarCampo`
- **Decisão**: Em `CmdAlterarCampo._aplicar_mutacao()`, após aplicar a mutação no alvo `msg`, se `self._caminho_msg` contiver pelo menos um separador `"."` e a mensagem `msg` resultante não possuir nenhum campo preenchido (`hasattr(msg, "ListFields") and len(msg.ListFields()) == 0`), subir pela cadeia de sufixos de `self._caminho_msg` verificando cada ancestral imediato `msg_pai`:
  - Se o segmento do caminho for um campo singular `FieldDescriptor.TYPE_MESSAGE` (`not is_repeated`) que **não** pertence a um `oneof` (`containing_oneof is None`), e `getattr(msg_pai, nome_sub).ListFields()` estiver vazio, chamar `msg_pai.ClearField(nome_sub)` e emitir `self.model.dado_alterado.emit(msg_pai, nome_sub)`.
- **Por que esta escolha**: Resolve a assimetria tanto quando um `Undo` reverte o primeiro campo preenchido de uma submensagem recém-ativada quanto quando o usuário apaga manualmente todos os campos de uma submensagem opcional (como `Coordenada` em `localizacao_estacionamento`), evitando que blocos vazios `localizacao_estacionamento: {}` vazem para o modelo ou para os arquivos Markdown/YAML.
- **Alternativas consideradas**:
  - *Converter edições de campos internos de `Coordenada` em substituição da submensagem inteira na UI*: descartado porque chamadas diretas a `CmdAlterarCampo` via controller ou ferramentas MCP (`aresta_alterar_campo` com caminho `<uid>.localizacao_estacionamento` e `campo="latitude"`) continuariam quebrando a simetria.

### 2. Resolução viva prioritária em `ComandoEditor._obter_msg()`
- **Decisão**: Em `ComandoEditor._obter_msg()`, quando `self.model is not None` e `self._caminho_msg is not None`, navegar primeiro na árvore ativa via `navegar_para_alvo(root, self._caminho_msg, indice_uids)`. Se encontrar a mensagem viva `alvo`, atualizar `self._msg_cache = alvo` e retorná-la. Somente se `navegar_para_alvo` retornar `None` (ex.: em testes isolados que limpam a árvore mas verificam o fallback de `_msg_cache`), retornar `self._msg_cache` se não for `None`.
- **Por que esta escolha**: Quando `msg_pai.ClearField(nome_sub)` é executado no `Undo`, a instância antiga em `self._msg_cache` é desanexada pelo `upb`. Ao priorizar `navegar_para_alvo`, o próximo `Redo` obtém `getattr(msg_pai, nome_sub)` (a nova instância vinculada ao `msg_pai`) e atualiza `self._msg_cache`, mantendo 100% de compatibilidade com os testes existentes de `_msg_cache`.

### 3. Rebinding automático de submensagens em `WidgetMensagemCoordenada` e `WidgetFormularioPadrao`
- **Decisão**:
  - Permitir que `WidgetMensagemCoordenada` receba opcionalmente `(msg_pai, nome_campo_no_pai)` (ou resolva sua propriedade `msg` dinamicamente via `getattr(self._msg_pai, self._campo_pai)` quando configurado a partir de uma submensagem singular em `WidgetFormularioPadrao._render_field_inner`).
  - Além disso, em `WidgetMensagemCoordenada._on_model_dado_alterado`, reagir também quando `msg` emitido pelo sinal `dado_alterado` for `self._msg_pai` e `campo_nome == self._campo_pai`, atualizando `self.msg = getattr(self._msg_pai, self._campo_pai)` e recarregando os campos.
- **Por que esta escolha**: Como `WidgetFormularioPadrao` mantém os formulários construídos em `self.cached_forms`, re-vincular `self.msg` diretamente a partir de `(msg_pai, campo_pai)` garante que a UI nunca envie uma instância `Coordenada` órfã/desanexada ao `CroquiController`, sem precisar destruir e reconstruir o widget inteiro durante a digitação.

### 4. Textos descritivos nos comandos canônicos
- **Decisão**: Configurar `self.setText(...)` no `__init__` de `CmdAlterarCampo` (`f"Alterar {self.campo_nome}"`), `CmdAdicionarRepeated` (`f"Adicionar {self.campo_nome}[{self.index}]"`), `CmdRemoverRepeated` (`f"Remover {self.campo_nome}[{self.index}]"`), `CmdMoverRepeated` (`f"Mover {self.campo_nome}[{self.index_from}->{self.index_to}]"`), `CmdAlterarImagem` (`f"Alterar imagem {self.nome_arquivo}"`) e `CmdAlterarAnexo` (`f"Alterar anexo {self.nome_arquivo}"`).
- **Por que esta escolha**: Melhora a inspeção da `QUndoStack`, breadcrumbs do Sentry e mensagens de diagnóstico do `OraculosCaos`.

## Risks / Trade-offs

- **[Risco] Submensagens de `oneof` (ex.: `ArquivoSetor.conteudo` ou `Escalada.boulder`) serem limpas indevidamente quando vazias** → **Mitigação**: A poda verifica explicitamente `field_desc.containing_oneof is None` no descritor do pai. Campos pertencentes a qualquer `oneof` nunca são podados por essa regra.
- **[Risco] Outros widgets de submensagem singular `INLINE` além de `WidgetMensagemCoordenada` reterem referência órfã** → **Mitigação**: Em `WidgetFormularioPadrao._on_campo_alterado`, quando `dado_alterado(msg_pai, nome_sub)` for emitido para um campo registrado em `self.field_containers` cuja submensagem foi limpa, atualizar ou re-renderizar o container caso a identidade da submensagem tenha mudado.
