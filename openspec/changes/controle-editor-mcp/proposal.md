# Proposta: Controle Total do Editor Aresta via MCP (Model Context Protocol)

## Por que

Atualmente, a catalogação e anotação de croquis no Editor Aresta dependem exclusivamente de interação humana direta pela interface gráfica PySide6 ou de scripts de linha de comando que manipulam arquivos estáticos no disco (contornando o editor). Embora existam habilidades (*skills*) no ecossistema para extração de dados e conversão de guias em PDF, não há um canal de comunicação estruturado em tempo de execução para que agentes inteligentes de IA (como Google Antigravity, OpenAI Codex, Claude Desktop, Cursor e outros) possam controlar o editor interativo de forma contínua, inspecionar seu estado visual em tempo real e orquestrar modificações seguras no croqui.

Integrar o Editor Aresta ao protocolo aberto Model Context Protocol (MCP) resolve essa lacuna e permite que o próprio editor seja o motor central de mutação e serialização. Graças à arquitetura MVC, ao índice universal de UIDs (`IndiceUidsModel`) e ao Princípio VIII de `AGENTS.md` (que exige que toda alteração passe obrigatoriamente pela pilha de histórico de comandos `QUndoCommand`), é possível expor um catálogo de ferramentas reflexivo 1:1 com os comandos e controladores do editor, garantindo auditoria completa, segurança de transações e capacidade imediata de desfazer/refazer (`undo/redo`) qualquer ação realizada por agentes de IA.

## O Que Muda

- **Servidor MCP Embutido com Transporte Híbrido e Descoberta Multiplataforma**:
  - Implementação de um servidor MCP no processo do Editor Aresta operando em loopback local (`127.0.0.1`) na porta padrão determinística `27378` (mnemônico T9 para `AREST`, com fallback automático para portas adjacentes livres e persistência em `mcp_sessao.json` no diretório de dados multiplataforma `obter_diretorio_base_app()`).
  - Disponibilização de um utilitário de terminal leve (`python -m editor.mcp.bridge`) operando em `stdio` para clientes que utilizam subprocessos (Antigravity, Codex, Claude Desktop), redirecionando o tráfego JSON-RPC para o servidor local ativo.
- **Diálogo de Conexão de Agentes na Interface (`Conectar Agente de IA (MCP)`)**:
  - Ação no menu do Editor que exibe um diálogo com o status em tempo real do servidor MCP, a porta ativa e botões de cópia em 1 clique com os blocos de configuração prontos para Google Antigravity, OpenAI Codex, Claude Desktop e Cursor.
- **Despachante Thread-Safe para o Loop de Eventos Qt**:
  - Mecanismo que encaminha as chamadas assíncronas do servidor MCP para a thread principal da GUI do PySide6 sem risco de condições de corrida ou travamento da interface.
- **Catálogo de Ferramentas MCP 1:1 com Comandos do Editor e Endereçamento Híbrido por `UID`**:
  - Ferramentas correspondentes a todos os comandos do histórico (`CmdAlterarPrimitivo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdAlterarOneof`, `CmdAlterarRepeatedItem`, `CmdAlterarMultiplosRepeatedItems`, `CmdMoverRepeated`, `CmdMigrarSetor`, `CmdAlterarMetadadosCaminhoNovo`, `CmdAlterarCampoImagem`, `CmdSubstituirImagemMemoria`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown`, `CmdRenomearEscalada`, `CmdMacro` e `CmdAdicionarMapaArquivo`) além de operações topológicas do `MapasController`.
  - Suporte a endereçamento híbrido ancorado em `UID` (`IndiceUidsModel`, NanoID de 14 caracteres, ex: `V1StGXR8_Z5jdH` ou `V1StGXR8_Z5jdH.mapas.0`) com fallback para caminho posicional a partir da raiz (`picos.0`), retornando automaticamente o `uid` gerado em cada criação de entidade.
- **Ferramentas de Visão Multimodal e Inspeção Estrutural**:
  - Ferramenta `aresta_capturar_canvas` para capturar a visão renderizada do canvas gráfico (fotos de croqui ou mapas vetoriais com curvas Catmull-Rom e caixas de POIs) em formato PNG Base64, permitindo análise visual por modelos multimodais.
  - Ferramentas de inspeção da árvore estrutural do croqui (incluindo UIDs e caminhos formatados `Grupo > Setor > Escalada`) e da seleção atual da UI.
- **Ferramentas de Ciclo de Vida do Projeto e Workspace**:
  - Ferramentas para consultar o status do workspace, abrir um croqui local/experimental, acionar a compilação e validação em tempo real, salvar alterações, navegar a interface (`aresta_focar_elemento`) e manipular o histórico (`aresta_desfazer`, `aresta_refazer`).

## Capacidades

### Novas Capacidades
- `editor-controle-mcp`: Implementa o servidor de controle MCP no Editor Aresta com transporte híbrido (SSE/HTTP em `127.0.0.1:27378` e ponte `stdio`), diálogo de conexão rápida na UI, despacho thread-safe Qt, catálogo de ferramentas 1:1 mapeado aos comandos do histórico com endereçamento por `UID`/caminho, captura multimodal do canvas e controle do ciclo de vida do projeto.

### Capacidades Modificadas
*(Nenhuma capacidade existente tem seus requisitos alterados. A integração opera através dos controladores, modelos e comandos já estabelecidos.)*

## Impacto

- **Código e Módulos Afetados**:
  - Novo submódulo `editor/mcp/` contendo o servidor, a ponte de transporte `stdio`, o despachante Qt, o resolvedor de alvos por `UID`/caminho e o catálogo de ferramentas, com espelhamento estrito 1:1 de testes (`*_test.py`) sem mocks para classes internas.
  - Novo diálogo `editor/views/dialogos/dialogo_conexao_mcp.py` (e respectivo teste) integrado à `JanelaPrincipal` (`editor/legacy_views/area_principal.py`).
- **Dependências**:
  - Adição da biblioteca oficial `mcp` (Python SDK) no grupo de dependências `editor` do `pyproject.toml`.
  - Reutilização das bibliotecas `fastapi`, `uvicorn` e `httpx` já presentes nas dependências do editor.
- **Compatibilidade e Segurança**:
  - Nenhuma quebra de compatibilidade com versões anteriores ou com o formato Protobuf.
  - Escuta restrita a loopback local (`127.0.0.1`) protegida por token efêmero de sessão.
  - Todas as mutações acionadas por agentes passam pela pilha de histórico e diário de recuperação, garantindo total reversibilidade via `Ctrl+Z`.
