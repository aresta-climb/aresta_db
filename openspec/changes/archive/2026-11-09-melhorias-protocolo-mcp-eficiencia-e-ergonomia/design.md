# Design

## Context

Consulte `proposal.md` para a motivação e `specs/` para os contratos comportamentais.
O servidor MCP (`editor/mcp/`) atua como fachada sobre `CroquiModel`, `CroquiController` e `MapasController`. Toda mutação de estado precisa passar obrigatoriamente pela `QUndoStack` através dos 6 comandos folha canônicos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`) ou `CmdMacro` (Princípios II e VIII do `AGENTS.md`).

## Goals / Non-Goals

**Goals:**
- Filtrar em tempo $O(1)$ por descritor as extensões `[aresta.*]` e os campos `INVISIVEL` (exceto `uid`, `alvo_uid` e `pontos_uids`) tanto na serialização da árvore (`aresta_obter_arvore`) quanto na introspecção do schema (`aresta_obter_esquema_proto`).
- Disponibilizar `aresta_listar_escaladas` com cruzamento automático entre `Escalada.uid`, `Mapa.referencias` e `Mapa.pontos_de_interesse` (incluindo `mapas_gerais`).
- Suportar inserção unitária (`valor`) e em lote (`valores`) em `aresta_adicionar_repeated` retornando `uid`, `uid_gerado` e `uids_gerados`.
- Implementar `MapasController.remover_referencia` e `aresta_remover_referencia_mapa` usando `CmdAlterarCampo` e `CmdRemoverRepeated`.
- Suportar `preservar_campos_compativeis: bool = False` (opt-in) na troca de ramo `oneof` em `CroquiController` / MCP e incluir a lista de campos válidos nos `ValueError` de campo inexistente.

**Non-Goals:**
- Não alterar a visibilidade de campos na interface gráfica PySide6 (que continua lendo `(aresta.formato_na_ui)` diretamente).
- Não remover automaticamente vínculos de outras escaladas em `aresta_vincular_referencia_mapa` (desvinculações devem ser explícitas via `aresta_remover_referencia_mapa`).

## Decisions

### 1. Pré-computação $O(1)$ de `_CAMPOS_OCULTOS_MCP` a partir dos Descriptors do `croqui_pb2`
- **Decisão**: Em `editor/mcp/ferramentas_conhecimento.py`, construir na carga do módulo um dicionário imutável `_CAMPOS_OCULTOS_MCP: dict[str, frozenset[str]]` mapeando cada `Descriptor.full_name` para o conjunto de nomes de campos que possuem `(aresta.formato_na_ui) == INVISIVEL` ou cujo `message_type` possua `(aresta.mensagem_formato_na_ui) == INVISIVEL`, excluindo da lista de ocultação `{"uid", "alvo_uid", "pontos_uids"}`.
- **Racional**: A inspeção das `Extensions` dos `FieldOptions` e `MessageOptions` ocorre uma única vez na importação do módulo. Durante `aresta_obter_arvore` e `aresta_obter_esquema_proto`, a filtragem recursiva consulta ` Descriptor.full_name` em $O(1)$ e descarta chaves iniciadas por `"[aresta."`.
- **Alternativas consideradas**: Filtrar por regex ou lista hardcoded de nomes de campos. Rejeitado porque desacoplaria o filtro da fonte de verdade (`croqui.proto`).

### 2. Cruzamento `Escalada` $\leftrightarrow$ `Mapa` em `aresta_listar_escaladas`
- **Decisão**: Implementar `aresta_listar_escaladas` em `editor/mcp/ferramentas_visao.py` percorrendo todos os picos do `Croqui`:
  1. Coletar um índice `{alvo_uid: (rotulos_ordenados, pontos_uids_ordenados)}` varrendo `pico.mapas_gerais.conteudo.mapas` e os `mapas` de cada `Setor` (tanto setores diretos em `pico.setores_ou_grupos` quanto setores aninhados dentro de `Grupo`). Para cada `Referencia`, resolver cada `ponto_uid` em `pontos_de_interesse` do mesmo mapa para extrair seu `rotulo` (ou `rotulo` do primeiro nó `CIRCULO_IDENTIFICADOR` quando for `linha` sem `rotulo` de topo).
  2. Percorrer os setores (filtrando opcionalmente por `alvo_setor` via UID/caminho e por substring case-insensitive `filtro_nome`) e serializar cada `Escalada` em um dicionário plano: `uid`, `indice_no_setor`, `setor_uid`, `setor_nome`, `rotulos_mapa`, `pontos_uids`, `tipo`, `nome`, `dificuldade` (nome do Enum), `data_abertura` e `conquistadores`.

### 3. `aresta_adicionar_repeated` com `valor` / `valores` e retorno de `uid_gerado` / `uids_gerados`
- **Decisão**: Adicionar `CroquiController.adicionar_multiplos_repeated(msg, campo_nome, index_inicial, valores)` (que empilha um único `CmdAdicionarRepeated` quando `len(valores) == 1` ou um `CmdMacro` quando `len(valores) > 1`). Na ferramenta `aresta_adicionar_repeated`, aceitar `valor` (1 item) ou `valores` (lista não vazia de itens), retornando:
  - `"uid"`: primeiro `uid` gerado (retrocompatibilidade);
  - `"uid_gerado"`: presente quando exatamente 1 item é inserido;
  - `"uids_gerados"`: lista com os `uid`s gerados para cada item inserido;
  - `"indice"` / `"indice_inicial_inserido"` e `"tamanho"`.

### 4. `MapasController.remover_referencia` e `aresta_remover_referencia_mapa`
- **Decisão**: Em `MapasController.remover_referencia(msg_mapa_proxy, alvo_uid, pontos_uids=None) -> int`:
  - Varre `msg_mapa_proxy.referencias` de trás para frente procurando entradas com `ref.alvo_uid == alvo_uid`.
  - Se `pontos_uids` não for informado (ou for vazio), remove cada entrada correspondente com `CmdRemoverRepeated`.
  - Se `pontos_uids` for informado, filtra `novos_pontos = [p for p in ref.pontos_uids if p not in conjunto_remover]`. Se `novos_pontos` ficar vazio, usa `CmdRemoverRepeated`; caso contrário, se houver mudança, atualiza `referencias.{idx}` com `CmdAlterarCampo`.
  - Se mais de um comando for gerado, agrupa em `CmdMacro`. Retorna a quantidade de referências alteradas/removidas.

### 5. Preservação Opt-In (`preservar_campos_compativeis: bool = False`) em `oneof` e Campos Válidos em `ValueError`
- **Decisão**:
  - Em `CroquiController._construir_comandos_para_alvo`, `alterar_campo` e `alterar_em_lote`, adicionar `preservar_campos_compativeis: bool = False`. Na camada MCP (`aresta_alterar_campo` e `aresta_alterar_em_lote`), quando `preservar_campos_compativeis=True` e o campo alvo for uma variante de um `oneof` de submensagem (ou o próprio nome do `oneof`) cuja variante atualmente ativa na mensagem seja outra submensagem (ex.: `via_esportiva` ativa e alterando para `via_movel`), copiar previamente da submensagem ativa para a nova submensagem todos os campos presentes (`ListFields()`) que possuam o mesmo nome, tipo e `label` compatíveis (ou mesmo `enum_type`), **antes** de sobrescrever com os campos explicitamente fornecidos pelo chamador. Assim, o `CmdAlterarCampo` único empilhado na `QUndoStack` já recebe a nova submensagem completa e o `undo()` restaura a variante antiga em um único passo.
  - Em `validar_pertence_ao_croqui` e `_validar_campo_se_msg_existir` (`editor/commands/comandos_protobuf.py`), formatar a lista ordenada `campos_validos = sorted(set(msg.DESCRIPTOR.fields_by_name.keys()) | set(msg.DESCRIPTOR.oneofs_by_name.keys()))` na mensagem do `ValueError`.

## Risks / Trade-offs

- **[Risk] Ocultar acidentalmente `uid`, `alvo_uid` ou `pontos_uids` por terem `(aresta.formato_na_ui) = INVISIVEL` no `croqui.proto`** → Mitigation: Manter a constante explícita `_CAMPOS_ENDERECAMENTO_MCP = frozenset({"uid", "alvo_uid", "pontos_uids"})` excluída de `_CAMPOS_OCULTOS_MCP` e cobrir com testes comportamentais dedicados em `ferramentas_visao_test.py` e `ferramentas_conhecimento_test.py`.
- **[Risk] Cópia de campos incompatíveis entre variantes `oneof` (ex.: `dificuldade` em `Boulder` usa `GrauBoulder` enquanto `ViaEsportiva` usa `GrauVia`)** → Mitigation: Copiar um campo homônimo somente quando `f_origem.type == f_destino.type`, `f_origem.label == f_destino.label`, `f_origem.message_type == f_destino.message_type` e `f_origem.enum_type == f_destino.enum_type`.
