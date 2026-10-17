# Spec Delta: editor-controle-mcp

## Purpose

Permite que agentes autônomos e assistentes de inteligência artificial controlem e inspecionem o Editor Aresta em tempo real por meio do protocolo padronizado Model Context Protocol (MCP), com suporte a transporte híbrido (SSE e stdio), endereçamento por UID estável, despacho thread-safe e rastreabilidade total via histórico.

## ADDED Requirements

### Requirement: Servidor MCP Integrado com Transporte Híbrido
O Editor Aresta MUST disponibilizar um servidor local compatível com a especificação Model Context Protocol (MCP), operando em loopback (`127.0.0.1`) na porta padrão `27378` (com fallback automático para portas livres e registro em `mcp_sessao.json` no diretório base multiplataforma). O sistema MUST também disponibilizar uma ponte de terminal (`editor.mcp.bridge`) operando via `stdio` que repassa mensagens JSON-RPC ao servidor local.

#### Scenario: Inicialização e conexão na porta padrão ou fallback
- **WHEN** o Editor Aresta é inicializado
- **THEN** o servidor HTTP local inicia o endpoint `/mcp/sse` em `127.0.0.1` na porta `27378` (ou na próxima porta disponível caso ocupada), grava os metadados em `mcp_sessao.json` e aceita conexões de clientes MCP

#### Scenario: Conexão via ponte stdio para clientes baseados em subprocesso
- **WHEN** um agente externo (como Antigravity, Codex ou Claude Desktop) executa `python -m editor.mcp.bridge` via `stdio`
- **THEN** a ponte descobre a porta ativa do editor e repassa mensagens JSON-RPC de forma bidirecional e transparente

### Requirement: Diálogo de Conexão de Agentes na Interface
O Editor Aresta MUST exibir na interface gráfica uma opção para abrir o diálogo `Conectar Agente de IA (MCP)`, apresentando o status de execução do servidor local, o endereço ativo e botões para copiar a configuração pronta para os principais clientes MCP.

#### Scenario: Cópia de configuração de agente em um clique
- **WHEN** o usuário abre o diálogo `Conectar Agente de IA (MCP)` e aciona o botão de copiar configuração para Antigravity, Codex, Claude Desktop ou Cursor
- **THEN** o sistema copia para a área de transferência o bloco de configuração formatado com os caminhos e a porta correspondentes ao ambiente em execução

### Requirement: Despacho Thread-Safe para o Loop de Eventos Qt
Toda requisição de execução de ferramenta recebida pelo servidor MCP que envolva consulta ou alteração do estado da aplicação (`CroquiModel`, `IndiceUidsModel`, `QUndoStack` ou widgets da interface) MUST ser despachada para a thread principal da interface gráfica do PySide6 antes da sua execução, retornando o resultado assincronamente ao cliente MCP.

#### Scenario: Execução de comando a partir da thread do servidor MCP
- **WHEN** o cliente MCP invoca uma ferramenta de mutação enquanto o loop de eventos Qt está ativo na thread principal
- **THEN** o despachante encaminha a ação para a thread da GUI via eventos Qt, executa a ação com segurança e retorna o resultado sem travamento ou condições de corrida

### Requirement: Catálogo de Ferramentas MCP Mapeado a Comandos e Endereçamento por UID
O servidor MCP MUST expor ferramentas mapeadas um-para-um com a camada de comandos do histórico (`QUndoCommand`) e controladores do editor, aceitando endereçamento híbrido tanto por `UID` universal (`IndiceUidsModel`) quanto por sub-caminho relativo ou caminho posicional. Toda mutação MUST empilhar o respectivo comando no `GerenciadorHistorico` e retornar o `uid` das entidades criadas ou alteradas.

#### Scenario: Alteração de campo por UID universal ou caminho
- **WHEN** o cliente MCP chama `aresta_alterar_primitivo` informando o `uid` de uma entidade (ou caminho posicional), o nome do campo e o novo valor
- **THEN** o sistema resolve a mensagem alvo no modelo, executa `CmdAlterarPrimitivo` na pilha de histórico e atualiza o modelo e a interface

#### Scenario: Adição de entidade com geração e retorno imediato de UID
- **WHEN** o cliente MCP chama `aresta_adicionar_repeated` para criar um novo setor, grupo, escalada, botão ou ponto de interesse
- **THEN** o item é inserido com um `uid` NanoID válido gerado imediatamente e a resposta da ferramenta retorna o `uid` criado junto ao caminho atualizado

#### Scenario: Operações de mapas, imagens e renomeação sincronizada
- **WHEN** o cliente MCP invoca ferramentas de renomeação de escalada, alteração de imagem/markdown ou vinculação de referências em mapas
- **THEN** os respectivos comandos (`CmdRenomearEscalada`, `CmdAlterarCampoImagem`, `CmdInserirImagemMarkdown`, `CmdInserirBotaoMarkdown` ou ações do `MapasController`) são executados preservando as referências por `alvo_uid` e `pontos_uids`

#### Scenario: Agrupamento transacional em macro
- **WHEN** o cliente MCP executa `aresta_iniciar_macro`, despacha múltiplas alterações e conclui com `aresta_finalizar_macro`
- **THEN** todas as alterações intermediárias são agrupadas em um único `CmdMacro` no histórico, permitindo desfazer o pacote inteiro com um único comando de desfazer

### Requirement: Ferramentas de Visão e Captura Multimodal do Canvas
O servidor MCP MUST disponibilizar ferramentas que permitam ao agente inspecionar a representação visual do croqui, incluindo a captura gráfica do viewport ativo (editor de imagens, mapas ou janela) em formato PNG Base64 e a recuperação da árvore estrutural hierárquica com todos os `UID`s e caminhos legíveis.

#### Scenario: Captura de tela do canvas ativo
- **WHEN** o cliente MCP invoca a ferramenta `aresta_capturar_canvas`
- **THEN** o sistema captura o frame renderizado do viewport solicitado e retorna o bloco de imagem codificado em PNG Base64 compatível com modelos multimodais

#### Scenario: Leitura da árvore estrutural com UIDs e seleção corrente
- **WHEN** o cliente MCP consulta `aresta_obter_arvore` ou `aresta_obter_selecao_atual`
- **THEN** o sistema retorna a estrutura em JSON contendo os `uid`s universais, caminhos formatados (`Grupo > Setor > Escalada`), caminhos posicionais e o elemento em foco na interface

### Requirement: Controle do Ciclo de Vida do Projeto e Workspace
O servidor MCP MUST disponibilizar ferramentas para consultar e abrir croquis no workspace, disparar a compilação e validação do croqui, manipular o histórico (`desfazer`/`refazer`), focar elementos na interface e salvar no disco.

#### Scenario: Validação e compilação do croqui
- **WHEN** o cliente MCP chama a ferramenta `aresta_compilar`
- **THEN** o compilador do Aresta é executado sobre o estado atual e retorna o status de sucesso junto à lista estruturada de erros ou advertências

#### Scenario: Foco por UID e sincronização visual da interface
- **WHEN** o cliente MCP invoca `aresta_focar_elemento` passando o `uid` ou caminho de um setor, grupo, escalada ou mapa
- **THEN** a interface gráfica do editor seleciona e destaca visualmente o elemento correspondente para o usuário
