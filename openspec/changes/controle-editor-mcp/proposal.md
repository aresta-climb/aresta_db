# Proposta: Controle Total do Editor Aresta via MCP (Model Context Protocol)

## Por que

Atualmente, a catalogação e anotação de croquis no Editor Aresta dependem exclusivamente de interação humana direta pela interface gráfica PySide6 ou de scripts de linha de comando que manipulam arquivos estáticos no disco. Embora existam habilidades (*skills*) no ecossistema para extração de dados e conversão de guias em PDF, não há um canal de comunicação estruturado em tempo de execução para que agentes inteligentes de IA (como Claude Desktop, Cursor, Antigravity e outros) possam controlar o editor interativo de forma contínua, inspecionar seu estado visual em tempo real e orquestrar modificações seguras no croqui.

Integrar o Editor Aresta ao protocolo aberto Model Context Protocol (MCP) resolve essa lacuna. Graças à arquitetura MVC do editor e ao Princípio VII de `AGENTS.md`, que exige que toda alteração passe obrigatoriamente pela pilha de histórico de comandos (`QUndoCommand`), é possível expor um catálogo de ferramentas reflexivo 1:1 com os comandos do editor, garantindo auditoria completa, segurança de transações e capacidade imediata de desfazer/refazer (`undo/redo`) qualquer ação realizada por agentes de IA.

## O Que Muda

- **Servidor MCP Embutido com Transporte Híbrido**:
  - Implementação de um servidor MCP no processo do Editor Aresta utilizando Server-Sent Events (SSE) sobre HTTP local na porta de loopback.
  - Disponibilização de um utilitário de terminal leve (`aresta-mcp` / `python -m editor.mcp.bridge`) operando em `stdio` para clientes que não suportam conexões SSE diretas, redirecionando o tráfego JSON-RPC para o servidor local.
- **Despachante Thread-Safe para o Loop de Eventos Qt**:
  - Mecanismo que encaminha as chamadas assíncronas do servidor MCP para a thread principal da GUI do PySide6 sem risco de condições de corrida ou travamento da interface.
- **Catálogo de Ferramentas MCP 1:1 com Comandos do Editor**:
  - Ferramentas correspondentes aos comandos fundamentais (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarOneof`, `CmdMoverRepeated`, `CmdRenomearEscalada`, `CmdMacro`, `CmdAdicionarMapaArquivo`).
  - Uso do sistema existente de caminhos por string (ex: `setores.0.vias.1`) para resolução direta de entidades no Protobuf.
- **Ferramentas de Visão e Multimodalidade**:
  - Ferramenta `aresta_capturar_canvas` para capturar a visão renderizada do canvas gráfico (fotos com traçados Catmull-Rom ou mapas) em formato de imagem base64 ou link SSE, permitindo análise visual por modelos multimodais.
  - Recursos e ferramentas de inspeção da árvore estrutural do croqui e do elemento atualmente selecionado na UI.
- **Ferramentas de Ciclo de Vida do Projeto e Interface**:
  - Ferramentas para acionar a compilação e validação do croqui em tempo real, salvar alterações, navegar a interface (`focar_elemento`) e manipular o histórico (`desfazer`, `refazer`).

## Capacidades

### Novas Capacidades
- `editor-controle-mcp`: Implementa o servidor de controle MCP no Editor Aresta com transporte híbrido (SSE HTTP e ponte stdio), catálogo de ferramentas 1:1 mapeado aos comandos do histórico, captura multimodal do canvas e ciclo de vida do projeto.

### Capacidades Modificadas
*(Nenhuma capacidade existente tem seus requisitos alterados. A integração opera através dos controladores e comandos já estabelecidos.)*

## Impacto

- **Código e Módulos Afetados**:
  - Novo submódulo `editor/mcp/` contendo o servidor, a ponte de transporte, o despachante Qt e o registro de ferramentas.
  - Ponto de integração no ciclo de vida do aplicativo (`editor/main.py` e `editor/legacy_views/area_principal.py`) para inicializar o serviço MCP junto com o editor.
- **Dependências**:
  - Adição da biblioteca oficial `mcp` (Python SDK) no grupo de dependências `editor` do `pyproject.toml`.
  - Reutilização das bibliotecas `fastapi` e `uvicorn` já presentes nas dependências do editor.
- **Compatibilidade e Segurança**:
  - Nenhuma quebra de compatibilidade com versões anteriores ou com o formato Protobuf.
  - Todas as mutações acionadas por agentes passam pela pilha de histórico e diário de recuperação, garantindo total reversibilidade via `Ctrl+Z`.
