# Design Técnico: Controle Total do Editor Aresta via MCP

## Context

O Editor Aresta é uma aplicação desktop desenvolvida em PySide6 (Qt para Python) estruturada sob uma arquitetura MVC rigorosa:
- **`models/`**: O [`CroquiModel`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/models/croqui_model.py) encapsula a árvore de dados Protobuf (`Croqui`) e expõe métodos somente-leitura e sinais reativos Qt.
- **`commands/`**: A camada de comandos [`editor/commands/comandos_protobuf.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/commands/comandos_protobuf.py) concentra todas as mutações possíveis através de subclasses de `QUndoCommand` (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMacro`, `CmdRenomearEscalada`, etc.).
- **`core/historico.py`**: O [`GerenciadorHistorico`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/historico.py) gerencia o `QUndoStack` e a sincronização append-only com o diário de recuperação (`diario_pendente.bin`).
- **Servidor HTTP Existente**: O editor já utiliza FastAPI e Uvicorn (ver [`servidor_celular.py`](file:///c:/Renato/Devel/aresta-climb/aresta_db/editor/core/servidor_celular.py)) para servir a prévia mobile em background.

Ver motivação detalhada em `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Prover um servidor MCP embutido no processo do editor via transporte SSE HTTP local (`127.0.0.1`).
- Prover um script ponte leve (`aresta-mcp` / `editor.mcp.bridge`) operando via `stdio` para clientes que não suportam conexão SSE direta (ex: Claude Desktop padrão).
- Garantir segurança de concorrência com um despachante thread-safe que delega execuções de ferramentas para a thread principal da GUI Qt.
- Expor ferramentas MCP com mapeamento 1:1 para os comandos `Cmd*` existentes, usando endereçamento universal por string de caminho (ex: `setores.0.vias.1`).
- Oferecer ferramentas de visão multimodal (`aresta_capturar_canvas`) para modelos de linguagem visual inspecionarem o canvas do editor.
- Oferecer ferramentas de ciclo de vida do croqui: compilação/validação, salvamento, histórico (`undo`/`redo`) e navegação na UI (`focar_elemento`).

**Non-Goals:**
- Implementar interface visual de chat (copiloto embutido na janela do editor) nesta fase — essa funcionalidade foi expressamente desacoplada para uma mudança futura.
- Expor o servidor MCP para a internet aberta (a comunicação é restrita a loopback local `127.0.0.1`).
- Criar comandos de mutação direta que ignorem a pilha de histórico `QUndoStack`.

## Decisions

### Decisão 1: Transporte Híbrido (Servidor SSE Nativo + Ponte `stdio`)
* **Escolha**: O Editor Aresta roda um servidor FastAPI/Starlette com endpoint SSE em segundo plano durante sua execução. Um módulo de CLI leve (`editor.mcp.bridge`) é fornecido para ser lançado por clientes MCP convencionais via `stdio`, repassando mensagens JSON-RPC para a porta local.
* **Alternativas consideradas**:
  - *Rodar o editor inteiro como subprocesso `stdio`*: Inviável, pois o editor possui interface gráfica, logs de depuração e verificação de instância única que interferem no canal stdin/stdout.
  - *Apenas SSE*: Deixaria usuários de clientes como Claude Desktop sem suporte direto sem ferramentas de terceiros.
* **Descoberta de Porta**: O editor grava a porta ativa e um token de autenticação local em um arquivo efêmero `~/.aresta/mcp_sessao.json` ou usa uma porta padronizada (ex: `8765`), permitindo que a ponte `stdio` localize a instância ativa imediatamente.

### Decisão 2: Despachante Thread-Safe Qt (`DespachanteQt`)
* **Escolha**: Uma classe utilitária utiliza `QTimer.singleShot(0, ...)` e `concurrent.futures.Future` para enfileirar as chamadas vindas da thread assíncrona do FastAPI/MCP diretamente no loop de eventos da thread da GUI do Qt, aguardando a finalização com timeout configurável.
* **Alternativas consideradas**:
  - *Executar métodos do `CroquiModel` diretamente na thread assíncrona*: Causaria condições de corrida e travamento imediato no subsistema de desenho e sinais do PySide6.

### Decisão 3: Mapeamento 1:1 com Comandos e Endereçamento Canônico por Caminho
* **Escolha**: Utilizar as funções existentes `resolver_caminho_mensagem` e `navegar_para_mensagem` de `comandos_protobuf.py`. A ferramenta MCP recebe o caminho (`"setores.0.vias.2"`), resolve a entidade correspondente no `CroquiModel`, instancia o comando específico (ex: `CmdAlterarPrimitivo`) e o envia ao `GerenciadorHistorico`.
* **Alternativas consideradas**:
  - *Criar dezenas de ferramentas especializadas para cada propriedade do Protobuf*: Violaria o Princípio VI (Simplicidade e Anti-Abstração) e aumentaria o consumo de tokens de contexto do modelo de IA.

### Decisão 4: Captura Multimodal do Canvas (`aresta_capturar_canvas`)
* **Escolha**: Executar a captura do widget visual ativo (seja a visualização de fotos de vias ou o editor de mapas) através de `QPixmap.grabWidget()` ou renderização offscreen em buffer de imagem, codificando em PNG Base64 com o tipo de conteúdo padronizado `image` do MCP.

### Decisão 5: Suporte a Transações em Lote via `CmdMacro`
* **Escolha**: As ferramentas `aresta_iniciar_macro` e `aresta_finalizar_macro` permitem que o agente execute centenas de adições ou edições e as condense em uma única entrada atômica no `QUndoStack`, permitindo ao usuário reverter tudo com um único `Ctrl+Z`.

## Risks / Trade-offs

- **[Conflito de Porta ou Múltiplas Instâncias]** → Mitigação: O editor gera dinamicamente uma porta livre caso a padrão esteja ocupada e atualiza o arquivo de conexão local `mcp_sessao.json`.
- **[Segurança em Ambiente Local]** → Mitigação: O servidor HTTP escuta exclusivamente em `127.0.0.1` e valida um cabeçalho com token de sessão gerado aleatoriamente no arranque do editor.
- **[Tempo de Resposta em Operações de Compilação]** → Mitigação: A ferramenta `aresta_compilar` utiliza o pipeline de compilação em memória existente sem bloquear a UI por mais de 500ms.

## Migration Plan

1. Adicionar o pacote `mcp` ao grupo de dependências `editor` no `pyproject.toml`.
2. Implementar o pacote `editor/mcp/` com servidor, despachante e catálogo de ferramentas.
3. Conectar a inicialização do servidor MCP ao arranque da `JanelaPrincipal` em `editor/legacy_views/area_principal.py` e `editor/main.py`.
4. Disponibilizar o script ponte `editor/mcp/bridge.py` executável via `python -m editor.mcp.bridge`.
