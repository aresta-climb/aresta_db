# Design Técnico: Controle Total do Editor Aresta via MCP

## Context

O Editor Aresta é uma aplicação desktop multiplataforma (Windows, macOS e Linux Flatpak) desenvolvida em PySide6 estruturada sob uma arquitetura MVC rigorosa validada por [`editor/arquitetura_mvc_test.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/arquitetura_mvc_test.py):
- **`models/`**: O [`CroquiModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/croqui_model.py) encapsula a árvore de dados Protobuf (`Croqui`), expõe métodos somente-leitura, sinais reativos Qt e mantém o [`IndiceUidsModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/indice_uids_model.py) sincronizado com lookup $O(1)$ de entidades por `uid` (NanoID 8 caracteres).
- **`commands/`**: A camada de comandos ([`comandos_protobuf.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_protobuf.py) e [`comandos_mapas.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_mapas.py)) concentra todas as mutações em **6 comandos atômicos canônicos + `CmdMacro`** (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo` e `CmdMacro`), com resolução híbrida nativa (`navegar_para_alvo` / `validar_pertence_ao_croqui`). Pela Regra 3 de `arquitetura_mvc_test.py`, apenas `controllers/` e `commands/` podem instanciar classes `Cmd*`.
- **`controllers/`**: [`CroquiController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/croqui_controller.py) e [`MapasController`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/controllers/mapas_controller.py) atuam como fachada semântica do domínio, compondo `CmdMacro` internamente para operações compostas (migração de setor, inserção de imagem/botão no Markdown, adição de mapa com arquivo e atualização de múltiplos campos).
- **`core/historico.py`**: O [`GerenciadorHistorico`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/historico.py) gerencia o `QUndoStack` e a sincronização append-only com o diário de recuperação (`diario_pendente.bin`).
- **Pipeline de Salvamento e Compilação em RAM**: O salvamento do editor utiliza `CroquiModel.extrair_arquivos_e_serializar` com C LibYAML ([`editor/core/serializacao_util.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/serializacao_util.py)) e compila em memória via `workspace.processar_renomeacao_e_compilacao`.
- **Servidor HTTP Existente**: O grupo `editor` do `pyproject.toml` já inclui `fastapi`, `uvicorn` e `httpx` (utilizados em [`servidor_celular.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/servidor_celular.py)).

Ver motivação detalhada em `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Prover um servidor MCP JSON-RPC 2.0 embutido no processo do editor usando `fastapi` e `uvicorn` (zero dependências externas novas) operando em `127.0.0.1` na porta padrão `27378` (com fallback dinâmico, instruções de handshake e descoberta via `mcp_sessao.json`).
- Prover um script ponte leve (`python -m editor.mcp.bridge`) operando via `stdio` para clientes que iniciam subprocessos locais (Antigravity, Codex, Claude Desktop).
- Prover o diálogo `DialogoConexaoMcp` na interface do editor com indicador de status e botões para copiar a configuração pronta para os principais agentes de IA.
- Garantir segurança de concorrência com um despachante thread-safe (`DespachanteQt`) que delega execuções de ferramentas para a thread principal da GUI Qt.
- Blindar o ciclo de execução de comandos contra requisições inválidas de agentes em 3 camadas:
  1. **Camada MCP (`ferramentas_comandos.py`)**: coerção de JSON para tipos nativos Protobuf (`dict` -> `Message` via `ParseDict` com geração de `uid` NanoID, strings de `Enum` -> `int` validado contra `EnumDescriptor`, `base64` -> `bytes`).
  2. **Camada Controller (`CroquiController`)**: método canônico `alterar_campo` aceitando campo único ou lote `campos: dict[str, Any]` (instanciando todos os `CmdAlterarCampo` antes de executar um único `CmdMacro`, garantindo atomicidade *all-or-nothing* sem expor `iniciar_macro`/`finalizar_macro` ao MCP).
  3. **Camada Command e Histórico (`CmdAlterarCampo.__init__` e `GerenciadorHistorico`)**: rejeição imediata (*fail-fast* antes de `QUndoStack.push`) de campos `repeated` não indexados e de valores com tipos incompatíveis com o `FieldDescriptor`, somada ao decorador `@Slot(int)` explícito em `_on_index_changed` e proteção em `__getattr__` de `GerenciadorHistorico` para evitar erros `AttributeError: Slot 'GerenciadorHistorico::_on_index_changed(int)' not found.` no `qtPythonMetacall` do PySide6/Sentry.
- Expor ferramentas de visão multimodal (`aresta_capturar_canvas`), inspeção estrutural enriquecida (`aresta_obter_arvore` com suporte a inspeção de `campo` específico, coleções `repeated` e mapa explícito `tamanhos_repeated`) e conhecimento (`aresta_obter_esquema_proto`, `aresta_listar_skills`, `aresta_ler_skill`).
- Atualizar as *skills* do repositório (`.agents/skills/`) para instruir agentes a operarem prioritariamente via ferramentas MCP quando conectados ao editor.
- Cumprir integralmente as diretrizes do [`AGENTS.md`](file:///c:/Renato/Devel/aresta-climb/aresta_db/AGENTS.md): espelhamento 1:1 de arquivos `_test.py`, 100% de cobertura comportamental e proibição absoluta de `MagicMock` para código interno.

**Non-Goals:**
- Implementar interface visual de chat (copiloto embutido na janela do editor) nesta fase — adiada para uma mudança futura.
- Expor gerenciamento manual de macros (`aresta_iniciar_macro` / `aresta_finalizar_macro`) via MCP — toda composição de `CmdMacro` ocorre de forma atômica e encapsulada dentro dos métodos do `CroquiController`.
- Permitir substituição integral de listas `repeated` via `CmdAlterarCampo` sem índice — bloqueado intencionalmente para preservar UIDs e o rastreamento de imagens órfãs em RAM de `CmdRemoverRepeated`.
- Expor o servidor MCP para a internet aberta (a comunicação é restrita a loopback local `127.0.0.1`).
- Adicionar pacotes externos novos ao `pyproject.toml` ou `uv.lock`.

## Decisions

### Decisão 1: Implementação Direta do Protocolo MCP sobre FastAPI + httpx com `instructions` no Handshake
* **Escolha**: O protocolo MCP é baseado em JSON-RPC 2.0 (`initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `resources/list`, `resources/read`). O Editor Aresta expõe esses métodos diretamente em um aplicativo FastAPI em segundo plano vinculado a `127.0.0.1` na porta inicial **`27378`**, suportando tanto `POST /mcp` quanto `GET /mcp/sse` + `POST /mcp/messages`. No retorno de `initialize`, o servidor inclui o campo `instructions` orientando o agente a consultar `aresta_obter_esquema_proto` e `aresta_listar_skills` antes de realizar mutações.
* **Descoberta de Sessão**: O editor grava a porta ativa em `obter_diretorio_base_app() / "mcp_sessao.json"`. A ponte `stdio` (`editor.mcp.bridge`) lê linhas JSON-RPC do `stdin`, faz `POST /mcp` local e devolve a resposta no `stdout`.

### Decisão 2: Superfície Canônica no `CroquiController` e Remoção de Macros Manuais no MCP
* **Escolha**: Alinhar o `editor/mcp/ferramentas_comandos.py` diretamente à taxonomia canônica de comandos introduzida em `comandos_protobuf.py`, tendo o `CroquiController` e o `MapasController` como fachada exclusiva:
  1. `CroquiController.alterar_campo(alvo, campo_nome=..., valor_novo=..., campos=...)`: aceita alterar um único campo ou um dicionário `campos: dict[str, Any]`. Quando recebe múltiplos campos, instancia primeiro todos os `CmdAlterarCampo` (validando todos no `__init__` antes de mutar qualquer estado) e os executa em um único `CmdMacro`.
  2. No MCP, as antigas ferramentas fragmentadas (`aresta_alterar_primitivo`, `aresta_alterar_oneof`, `aresta_alterar_item_repeated`, `aresta_alterar_multiplos_repeated`, `aresta_renomear_escalada`, `aresta_iniciar_macro`, `aresta_finalizar_macro`) são consolidadas em `aresta_alterar_campo`, mantendo `aresta_adicionar_repeated`, `aresta_remover_repeated`, `aresta_mover_repeated`, `aresta_migrar_setor`, `aresta_alterar_imagem`, `aresta_alterar_campo_imagem`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown`, `aresta_adicionar_mapa_arquivo` e `aresta_vincular_referencia_mapa`.

### Decisão 3: Arquitetura de Validação Defensiva e Coerção em 3 Camadas + Blindagem Qt/Shiboken
* **Problema Raiz Identificado**: Quando `QUndoStack.push(cmd)` é invocado em C++ pelo PySide6, ele chama virtualmente `cmd.redo()`. Se uma exceção Python ocorre dentro de `redo()` (por exemplo, `AttributeError` ao tentar atribuir a um campo `repeated` sem índice ou `TypeError` ao atribuir `dict`/tipo inválido no Protobuf), o C++ `QUndoStack::push` não aborta: ele mantém o comando defeituoso na pilha, emite `indexChanged(int)` e chama `PyErr_Print()`, disparando o `sys.excepthook` (Sentry) e limpando a exceção Python (fazendo o MCP retornar falso sucesso). Além disso, em `GerenciadorHistorico`, a ausência de `@Slot(int)` em `_on_index_changed` combinada com `__getattr__` em subclasse de `QObject` faz o `SignalManagerPrivate::qtPythonMetacall` do Shiboken reportar `AttributeError: Slot 'GerenciadorHistorico::_on_index_changed(int)' not found.`.
* **Escolha**:
  ```text
  [1. MCP: ferramentas_comandos.py]
    Coerção JSON -> Protobuf antes de chamar o Controller:
    - dict -> Message Protobuf via ParseDict (gerando uid NanoID se aplicável)
    - str em campo Enum (ex: "BR_7A") -> int via EnumDescriptor.values_by_name
    - Rejeita chaves desconhecidas ou enums inexistentes listando opções válidas
          │
          ▼
  [2. Controller: CroquiController]
    Orquestração tipada:
    - Instancia todos os ComandoEditor ANTES de chamar undo_stack.executar()
          │
          ▼
  [3. Command & Histórico: CmdAlterarCampo.__init__ + GerenciadorHistorico]
    Guarda-corpo final (Zero-Push-on-Invalid):
    - CmdAlterarCampo.__init__ rejeita `field_desc.is_repeated` sem `.indice` com ValueError
    - CmdAlterarCampo.__init__ valida compatibilidade de tipo de `valor_novo` com FieldDescriptor
    - GerenciadorHistorico._on_index_changed decorado com @Slot(int) e __getattr__ ignora `_*`
  ```

### Decisão 4: Inspeção de Dados (`aresta_obter_arvore`) com Suporte a `repeated` e `tamanhos_repeated`
* **Escolha**: Evoluir `aresta_obter_arvore` em `editor/mcp/ferramentas_visao.py` para aceitar `alvo` (UID ou caminho, vazio = raiz), `campo` (opcional: nome de campo primitivo, submensagem, `oneof` ou `repeated`) e `incluir_indice_uids` (opcional, padrão `True` apenas quando `alvo == ""` e `campo == ""`):
  - Se `campo` apontar para uma lista `repeated` (ou `alvo` resolver para um container `repeated`), serializa os itens individualmente sem chamar `MessageToDict` no container (evitando `AttributeError`) e retorna `{"caminho": ..., "campo": ..., "tipo_campo": "repeated", "tamanho": len(colecao), "itens": [...]}`.
  - Ao retornar uma mensagem Protobuf, inclui sempre o dicionário `"tamanhos_repeated": {nome_campo: len(getattr(msg, nome_campo))}` para todos os campos `repeated` definidos no `DESCRIPTOR` da mensagem (mesmo quando `0`, já que o Protobuf omite listas vazias em `MessageToDict`).

### Decisão 5: Introspecção do Schema `croqui.proto` e das `Skills` via MCP (`ferramentas_conhecimento.py`)
* **Escolha**: Criar `editor/mcp/ferramentas_conhecimento.py` (com testes em `ferramentas_conhecimento_test.py`) registrando:
  1. `aresta_obter_esquema_proto(tipo_mensagem: str = "")` (e recurso `aresta://esquema/proto`):
     - Sem `tipo_mensagem`: retorna o guia compacto de endereçamento e edição do MCP, a lista de todas as mensagens e enums do `croqui_pb2.DESCRIPTOR`, e o conteúdo de `aresta_api/proto/croqui.proto`.
     - Com `tipo_mensagem` (ex: `"Escalada"`, `"ConteudoSetor"`, `"GrauBrasileiro"`): inspeciona o `Descriptor`/`EnumDescriptor` correspondente e retorna seus campos (tipo, se é `repeated`, variante de `oneof`, valores de `Enum` permitidos) enriquecidos com os comentários extraídos por `editor/core/proto_comments.py`.
  2. `aresta_listar_skills()` e `aresta_ler_skill(nome_skill: str)` (e recursos `aresta://skills`):
     - Lê dinamicamente os diretórios em `.agents/skills/*/SKILL.md`, extraindo nome e descrição do frontmatter YAML e retornando o conteúdo completo da skill solicitada.

### Decisão 6: Unificação do Resolvedor de Alvo (`resolvedor_alvo.py`)
* **Escolha**: Simplificar `editor/mcp/resolvedor_alvo.py` delegando a resolução de mensagens para `navegar_para_alvo` e `validar_pertence_ao_croqui` de `editor/commands/comandos_protobuf.py`, mantendo apenas o desempacotamento ergonômico de variantes ativas (`Escalada` -> variante ativa de `tipo`, `SetorOuGrupo` / `ArquivoSetor` -> `.conteudo`) quando o campo solicitado pertence ao sub-objeto de conteúdo.

## Risks / Trade-offs

- **[Conflito de Porta `27378`]** → Mitigação: Busca sequencial automática a partir de `27378` (`27378..27390`) ou porta efêmera livre do SO, persistida em `mcp_sessao.json` e exibida no `DialogoConexaoMcp`.
- **[Payloads JSON Inválidos de Agentes]** → Mitigação: Coerção e validação determinística na camada MCP + validação estrita de invariantes no `__init__` dos comandos antes de `QUndoStack.push`, retornando erros JSON-RPC descritivos com a lista de campos ou valores de `Enum` válidos sem acionar o Sentry.
- **[Regras de Arquitetura MVC]** → Mitigação: Verificação contínua com `pytest editor/arquitetura_mvc_test.py` garantindo zero instanciações de `Cmd*` fora de `controllers/` e `commands/` e zero uso de comandos legados.

## Migration Plan

1. Blindar `GerenciadorHistorico` (`editor/core/historico.py`) com `@Slot(int)` e guarda em `__getattr__`, e blindar `CmdAlterarCampo.__init__` (`editor/commands/comandos_protobuf.py`) contra `repeated` sem índice e tipos incompatíveis.
2. Adicionar o método canônico `alterar_campo` (com suporte a lote `campos: dict[str, Any]` via `CmdMacro`) em `CroquiController` (`editor/controllers/croqui_controller.py`).
3. Refatorar `editor/mcp/ferramentas_comandos.py` e `editor/mcp/resolvedor_alvo.py` para expor a interface canônica do `CroquiController` com coerção JSON -> Protobuf (`dict` -> `Message`, `str` -> `Enum`), removendo `aresta_iniciar_macro`/`aresta_finalizar_macro` e ferramentas legadas redundantes.
4. Evoluir `aresta_obter_arvore` em `editor/mcp/ferramentas_visao.py` para suportar inspeção de `campo`/`repeated` e retornar `tamanhos_repeated`.
5. Implementar `editor/mcp/ferramentas_conhecimento.py` (`aresta_obter_esquema_proto`, `aresta_listar_skills`, `aresta_ler_skill`), registrar `instructions` no `ServidorMCP` e atualizar as *skills* em `.agents/skills/` e `docs/mcp.md`.
