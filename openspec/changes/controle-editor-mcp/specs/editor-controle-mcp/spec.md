# Spec Delta: editor-controle-mcp

## Purpose

Permite que agentes autônomos e assistentes de inteligência artificial controlem e inspecionem o Editor Aresta em tempo real por meio do protocolo padronizado Model Context Protocol (MCP), com suporte a transporte híbrido (SSE e stdio), despacho thread-safe e rastreabilidade total via histórico.

## ADDED Requirements

### Requirement: Servidor MCP Integrado com Transporte Híbrido
O Editor Aresta MUST disponibilizar um servidor local compatível com a especificação Model Context Protocol (MCP), operando via Server-Sent Events (SSE) sobre HTTP local na porta de loopback. Adicionalmente, o sistema MUST disponibilizar um executável utilitário de terminal (`aresta-mcp`) capaz de operar via entrada e saída padrão (`stdio`) para atuar como ponte e repassar mensagens JSON-RPC para o servidor SSE local.

#### Scenario: Inicialização e conexão via SSE HTTP local
- **WHEN** o Editor Aresta é inicializado com a flag ou configuração de MCP ativa
- **THEN** o servidor HTTP local inicia o endpoint `/mcp/sse` e aceita conexões de clientes MCP compatíveis

#### Scenario: Conexão via ponte stdio para clientes legados
- **WHEN** um cliente externo de IA executa a ferramenta de linha de comando `aresta-mcp` via `stdio`
- **THEN** a ponte se conecta ao servidor SSE local do editor e repassa mensagens JSON-RPC de forma bidirecional e transparente

### Requirement: Despacho Thread-Safe para o Loop de Eventos Qt
Toda e qualquer requisição de execução de ferramenta recebida pelo servidor MCP que envolva consulta ou alteração do estado da aplicação (`CroquiModel`, `QUndoStack` ou widgets da interface) MUST ser despachada para a thread principal da interface gráfica do PySide6 antes da sua execução, retornando o resultado assincronamente ao cliente MCP.

#### Scenario: Execução de comando a partir da thread do servidor MCP
- **WHEN** o cliente MCP invoca uma ferramenta de mutação enquanto o loop de eventos Qt está ativo na thread principal
- **THEN** o despachante encaminha a ação para a thread da GUI via eventos Qt, executa a ação com segurança e retorna o resultado sem travamento ou condições de corrida

### Requirement: Catálogo de Ferramentas MCP Mapeado a Comandos
O servidor MCP MUST expor ferramentas que realizam mapeamento direto um-para-um com a camada de comandos do histórico (`QUndoCommand`). Toda alteração de dados no croqui solicitada via ferramenta MCP MUST gerar e empilhar o respectivo comando na pilha `QUndoStack` (`GerenciadorHistorico`), garantindo persistência no diário pendente e atualização reativa dos componentes gráficos.

#### Scenario: Alteração de campo primitivo
- **WHEN** o cliente MCP chama a ferramenta `aresta_alterar_primitivo` informando caminho, campo e novo valor
- **THEN** um comando `CmdAlterarPrimitivo` é executado na pilha de histórico, o valor é atualizado no modelo e o histórico ganha uma nova entrada passível de desfeita

#### Scenario: Adição e remoção de itens em campos repeated
- **WHEN** o cliente MCP chama `aresta_adicionar_repeated` ou `aresta_remover_repeated` para um caminho de setor ou via
- **THEN** o item correspondente é inserido ou removido no modelo através do respectivo `QUndoCommand` e a interface visual reflete a mudança

#### Scenario: Agrupamento transacional em macro
- **WHEN** o cliente MCP executa `aresta_iniciar_macro`, despacha múltiplas alterações e conclui com `aresta_finalizar_macro`
- **THEN** todas as alterações intermediárias são agrupadas em um único `CmdMacro` no histórico, permitindo desfazer o bloco inteiro com um único comando de desfazer

### Requirement: Ferramentas de Visão e Captura Multimodal do Canvas
O servidor MCP MUST disponibilizar ferramentas e recursos que permitam ao agente inspecionar a representação visual do croqui, incluindo a captura gráfica do viewport ativo (editor de imagens, mapas ou janela) em formato de imagem e a recuperação da árvore estrutural hierárquica do croqui aberto.

#### Scenario: Captura de tela do canvas ativo
- **WHEN** o cliente MCP invoca a ferramenta `aresta_capturar_canvas`
- **THEN** o sistema captura o frame renderizado do viewport ativo e retorna o conteúdo codificado em PNG com cabeçalho MIME apropriado para modelos multimodais

#### Scenario: Leitura da árvore estrutural e seleção corrente
- **WHEN** o cliente MCP consulta o recurso ou ferramenta de inspeção estrutural
- **THEN** o sistema retorna a árvore em formato JSON detalhando os nós (picos, setores, vias), caminhos de endereçamento e o elemento atualmente em foco na interface

### Requirement: Controle do Ciclo de Vida do Projeto e Interface
O servidor MCP MUST disponibilizar ferramentas para disparar o processo de compilação/validação do croqui, manipulação do histórico (`desfazer`/`refazer`), navegação da interface e salvamento no disco.

#### Scenario: Validação e compilação do croqui
- **WHEN** o cliente MCP chama a ferramenta `aresta_compilar`
- **THEN** o compilador do Aresta é executado sobre o estado em memória e retorna o status de sucesso junto à lista de erros ou advertências encontrados

#### Scenario: Foco e sincronização visual da interface
- **WHEN** o cliente MCP invoca `aresta_focar_elemento` passando o caminho de um setor ou via
- **THEN** a interface gráfica do editor seleciona e destaca visualmente o elemento correspondente para o usuário
