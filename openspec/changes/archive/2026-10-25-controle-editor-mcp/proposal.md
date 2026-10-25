# Proposta: Controle Total do Editor Aresta via MCP (Model Context Protocol)

## Por que

Atualmente, a catalogação e anotação de croquis no Editor Aresta dependem exclusivamente de interação humana direta pela interface gráfica PySide6 ou de scripts de linha de comando que manipulam arquivos estáticos no disco (contornando o editor). Embora existam habilidades (*skills*) no ecossistema para extração de dados e conversão de guias em PDF, não há um canal de comunicação estruturado em tempo de execução para que agentes inteligentes de IA (como Google Antigravity, OpenAI Codex, Claude Desktop, Cursor e outros) possam controlar o editor interativo de forma contínua, inspecionar seu estado visual em tempo real e orquestrar modificações seguras no croqui.

Integrar o Editor Aresta ao protocolo aberto Model Context Protocol (MCP) resolve essa lacuna e permite que o próprio editor seja o motor central de mutação e serialização. Graças à arquitetura MVC, ao índice universal de UIDs (`IndiceUidsModel`), à unificação reflexiva de comandos (`CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated`, `CmdAlterarImagem`, `CmdAlterarAnexo`, `CmdMacro`) e ao Princípio VIII de `AGENTS.md` (que exige que toda alteração passe obrigatoriamente pela pilha de histórico de comandos `QUndoCommand` via Controllers), é possível expor um catálogo enxuto de ferramentas canônicas via Controllers com validação defensiva estrita, introspecção de schema Protobuf e acesso direto às *skills* do projeto.

## O Que Muda

- **Servidor MCP Embutido com Transporte Híbrido, Instruções de Handshake e Descoberta Multiplataforma**:
  - Implementação de um servidor MCP JSON-RPC 2.0 no processo do Editor Aresta (usando `fastapi` e `uvicorn` já presentes no projeto) operando em loopback local (`127.0.0.1`) na porta padrão determinística `27378` (mnemônico T9 para `AREST`, com fallback automático para portas adjacentes livres e persistência em `mcp_sessao.json` no diretório de dados multiplataforma `obter_diretorio_base_app()`).
  - Inclusão do bloco `instructions` no handshake `initialize` do MCP orientando imediatamente qualquer agente conectado sobre o uso de `aresta_obter_esquema_proto`, `aresta_listar_skills` e endereçamento por `UID`.
  - Disponibilização de um utilitário de terminal leve (`python -m editor.mcp.bridge`) operando em `stdio` para clientes que utilizam subprocessos (Antigravity, Codex, Claude Desktop), redirecionando o tráfego JSON-RPC para o servidor local ativo.
- **Diálogo de Conexão de Agentes na Interface (`Conectar Agente de IA (MCP)`)**:
  - Ação no menu do Editor que exibe um diálogo com o status em tempo real do servidor MCP, a porta ativa e botões de cópia em 1 clique com os blocos de configuração prontos para Google Antigravity, OpenAI Codex, Claude Desktop e Cursor.
- **Despachante Thread-Safe Qt e Blindagem do `GerenciadorHistorico`**:
  - Mecanismo que encaminha as chamadas assíncronas do servidor MCP para a thread principal da GUI do PySide6 sem condições de corrida.
  - Blindagem de `GerenciadorHistorico` (`@Slot(int)` explícito em `_on_index_changed` e proteção em `__getattr__` contra atributos privados/internos) e validação *fail-fast* no `__init__` de `CmdAlterarCampo` (rejeitando campos `repeated` sem índice e tipos incompatíveis antes de `QUndoStack.push`), impedindo exceções C++/Shiboken no Sentry ou comandos corrompidos na pilha.
- **Catálogo de Ferramentas MCP Canônicas via Controllers e Endereçamento Híbrido por `UID`**:
  - Alinhamento 1:1 com a interface canônica de `CroquiController` e `MapasController` (respeitando a Regra 3 de `arquitetura_mvc_test.py`), substituindo comandos fragmentados de baixo nível por:
    - `aresta_alterar_campo` (despachado via `CroquiController.alterar_campo`, aceitando um único campo ou um lote `campos: dict[str, Any]` agrupado atomicamente em `CmdMacro` pelo Controller; resolve automaticamente via reflection se o alvo é `primitivo`, item indexado `campo.0`, `oneof`, `submensagem` ou `extensao`, além de converter `dict` JSON em `Message` Protobuf e nomes de `Enum` em inteiros na fronteira MCP).
    - `aresta_adicionar_repeated`, `aresta_remover_repeated` e `aresta_mover_repeated` (com geração automática de `uid` NanoID de 8 caracteres e retorno do `tamanho` atualizado da coleção).
    - Operações compostas encapsuladas no Controller (`aresta_migrar_setor`, `aresta_alterar_imagem`, `aresta_alterar_campo_imagem`, `aresta_inserir_imagem_markdown`, `aresta_inserir_botao_markdown`, `aresta_adicionar_mapa_arquivo` e `aresta_vincular_referencia_mapa`), sem expor gerenciamento manual de macros (`iniciar_macro`/`finalizar_macro`) ao agente.
- **Ferramentas de Visão Multimodal, Inspeção de Dados (`repeated` / tamanhos) e Conhecimento (`croqui.proto` e `Skills`)**:
  - Ferramenta `aresta_capturar_canvas` para capturar a visão renderizada do canvas gráfico em formato PNG Base64.
  - Evolução de `aresta_obter_arvore` para suportar inspeção de um `campo` específico (incluindo coleções `repeated` inteiras ou indexadas sem falhar em `MessageToDict`), retornar `tamanhos_repeated: dict[str, int]` em todas as mensagens inspecionadas (mesmo quando vazias `0`) e omitir o `indice_uids` global por padrão em consultas a sub-alvos.
  - Novo módulo `editor/mcp/ferramentas_conhecimento.py` expondo `aresta_obter_esquema_proto` (esquema `croqui.proto`, tipos de campos, variantes de `oneof`, valores de `Enum` e docstrings de `proto_comments.py`), `aresta_listar_skills` e `aresta_ler_skill` (com atualização das skills em `.agents/skills/` para orientar o uso das ferramentas MCP quando conectado ao editor).
- **Ferramentas de Ciclo de Vida do Projeto e Workspace**:
  - Ferramentas para consultar o status do workspace, acionar o pipeline unificado de salvamento e compilação em memória RAM, navegar a interface (`aresta_focar_elemento`) e manipular o histórico (`aresta_desfazer`, `aresta_refazer`).

## Capacidades

### Novas Capacidades
- `editor-controle-mcp`: Implementa o servidor de controle MCP no Editor Aresta com transporte híbrido (SSE/HTTP em `127.0.0.1:27378` e ponte `stdio`), diálogo de conexão rápida na UI, despacho thread-safe Qt, blindagem do histórico e validação defensiva de comandos, catálogo de ferramentas canônicas via Controllers com coerção JSON->Protobuf e endereçamento por `UID`/caminho, inspeção de coleções `repeated`, exposição de schema `croqui.proto` e *skills*, captura multimodal do canvas e controle do ciclo de vida do projeto.

### Capacidades Modificadas
*(Nenhuma capacidade existente tem seus requisitos alterados. A integração opera através dos controladores, modelos e comandos canônicos já estabelecidos.)*

## Impacto

- **Código e Módulos Afetados**:
  - Submódulo `editor/mcp/` contendo o servidor JSON-RPC/SSE, a ponte de transporte `stdio`, o despachante Qt, o resolvedor de alvos, as ferramentas canônicas de comando, visão, ciclo de vida e conhecimento (`ferramentas_conhecimento.py`), com espelhamento estrito 1:1 de testes (`*_test.py`) sem mocks para classes internas.
  - Blindagem defensiva em `editor/core/historico.py` (`@Slot(int)` e guarda em `__getattr__`), `editor/commands/comandos_protobuf.py` (validação *fail-fast* de campos `repeated` não indexados e tipos no `__init__` de `CmdAlterarCampo`) e `editor/controllers/croqui_controller.py` (método canônico `alterar_campo` com suporte a lote atômico `campos: dict[str, Any]`).
  - Diálogo `editor/views/dialogos/dialogo_conexao_mcp.py` integrado à `JanelaPrincipal` (`editor/legacy_views/area_principal.py`).
  - Atualização das instruções nas *skills* em `.agents/skills/` e documentação em `docs/mcp.md`.
- **Dependências**:
  - Zero novas dependências externas no `pyproject.toml` ou `uv.lock`: reutiliza integralmente `fastapi`, `uvicorn` e `httpx` já instalados no grupo `editor`.
- **Compatibilidade e Segurança**:
  - Escuta restrita a loopback local (`127.0.0.1`).
  - Todas as mutações acionadas por agentes são validadas antes de entrar no `QUndoStack` e passam pela pilha de histórico e diário de recuperação, garantindo total reversibilidade via `Ctrl+Z`.
