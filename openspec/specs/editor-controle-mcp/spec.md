# editor-controle-mcp Specification

## Purpose

Permite que agentes autônomos e assistentes de inteligência artificial controlem e inspecionem o Editor Aresta em tempo real por meio do protocolo padronizado Model Context Protocol (MCP), com suporte a transporte híbrido (SSE e stdio), endereçamento por UID estável, despacho thread-safe, validação defensiva estrita, introspecção de schema Protobuf e skills, e rastreabilidade total via histórico.

## Requirements

### Requirement: Servidor MCP Integrado com Transporte Híbrido e Instruções de Handshake
O Editor Aresta MUST disponibilizar um servidor local compatível com a especificação Model Context Protocol (MCP), operando em loopback (`127.0.0.1`) na porta padrão `27378` (com fallback automático para portas livres e registro em `mcp_sessao.json` no diretório base multiplataforma). O retorno do método `initialize` MUST incluir o campo `instructions` orientando o agente a consultar o esquema Protobuf e as *skills* disponíveis. O sistema MUST também disponibilizar uma ponte de terminal (`editor.mcp.bridge`) operando via `stdio` que repassa mensagens JSON-RPC ao servidor local.

#### Scenario: Inicialização e conexão na porta padrão ou fallback com instruções
- **WHEN** o Editor Aresta é inicializado e um cliente MCP envia `initialize`
- **THEN** o servidor HTTP local responde em `127.0.0.1` na porta ativa (gravada em `mcp_sessao.json`) incluindo `instructions` com orientação de uso de `aresta_obter_esquema_proto`, `aresta_listar_skills` e endereçamento por `UID`

#### Scenario: Conexão via ponte stdio para clientes baseados em subprocesso
- **WHEN** um agente externo (como Antigravity, Codex ou Claude Desktop) executa `python -m editor.mcp.bridge` via `stdio`
- **THEN** a ponte descobre a porta ativa do editor e repassa mensagens JSON-RPC de forma bidirecional e transparente

### Requirement: Diálogo de Conexão de Agentes na Interface
O Editor Aresta MUST exibir na interface gráfica uma opção para abrir o diálogo `Conectar Agente de IA (MCP)`, apresentando o status de execução do servidor local, o endereço ativo e botões para copiar a configuração pronta para os principais clientes MCP.

#### Scenario: Cópia de configuração de agente em um clique
- **WHEN** o usuário abre o diálogo `Conectar Agente de IA (MCP)` e aciona o botão de copiar configuração para Antigravity, Codex, Claude Desktop ou Cursor
- **THEN** o sistema copia para a área de transferência o bloco de configuração formatado com os caminhos e a porta correspondentes ao ambiente em execução

### Requirement: Despacho Thread-Safe Qt e Blindagem do Histórico contra Comandos Inválidos
Toda requisição de execução de ferramenta recebida pelo servidor MCP que envolva consulta ou alteração do estado da aplicação (`CroquiModel`, `IndiceUidsModel`, `QUndoStack` ou widgets da interface) MUST ser despachada para a thread principal da interface gráfica do PySide6. O `GerenciadorHistorico` MUST registrar seu slot `_on_index_changed` com `@Slot(int)` e proteger `__getattr__` contra atributos privados/internos. O `CmdAlterarCampo` MUST validar os tipos e rejeitar campos `repeated` sem índice no `__init__` antes de qualquer empilhamento em `QUndoStack`.

#### Scenario: Execução de comando a partir da thread do servidor MCP
- **WHEN** o cliente MCP invoca uma ferramenta de mutação enquanto o loop de eventos Qt está ativo na thread principal
- **THEN** o despachante encaminha a ação para a thread da GUI via eventos Qt, executa a ação com segurança e retorna o resultado sem travamento ou condições de corrida

#### Scenario: Rejeição fail-fast de campo repeated sem índice ou tipo inválido antes do QUndoStack
- **WHEN** o cliente MCP ou chamador tenta alterar um campo `repeated` sem especificar `.indice` em `CmdAlterarCampo` (ex: `campo="creditos"`) ou envia um valor incompatível com o `FieldDescriptor`
- **THEN** a exceção `ValueError` ou `TypeError` é lançada durante a instanciação do comando antes de `QUndoStack.push`, nenhum comando é empilhado no histórico e o servidor MCP retorna `isError: True` com mensagem descritiva

### Requirement: Catálogo de Ferramentas MCP Canônicas via Controllers e Coerção JSON-Protobuf
O servidor MCP MUST expor ferramentas mapeadas à interface canônica de `CroquiController` e `MapasController`, aceitando endereçamento híbrido por `UID` universal (`IndiceUidsModel`), `<uid>.<subcaminho>` ou caminho posicional. A ferramenta `aresta_alterar_campo` MUST suportar tanto a alteração de um único campo quanto de um dicionário `campos` em lote (agrupado internamente em um `CmdMacro` pelo `CroquiController`), convertendo automaticamente dicionários JSON em submensagens Protobuf (ou variantes `oneof`) e nomes de `Enum` em seus valores inteiros correspondentes. O servidor MCP MUST NOT expor ferramentas manuais de abertura/fechamento de macro (`iniciar_macro`/`finalizar_macro`).

#### Scenario: Alteração unificada de campo primitivo, indexado, oneof, submensagem ou enum por nome
- **WHEN** o cliente MCP chama `aresta_alterar_campo` informando o `alvo` (UID ou caminho) e um `campo` + `valor` (seja primitivo, `campo.0`, variante `oneof` como `via_esportiva`, submensagem como `dict` ou `Enum` por string como `"BR_7A"`)
- **THEN** a camada MCP converte o JSON para o tipo Protobuf correspondente, despacha via `CroquiController.alterar_campo` executando `CmdAlterarCampo` no histórico e retorna o estado atualizado

#### Scenario: Alteração atômica de múltiplos campos em lote no mesmo alvo
- **WHEN** o cliente MCP chama `aresta_alterar_campo` informando `alvo` e um dicionário `campos` com múltiplas chaves e valores
- **THEN** o `CroquiController` valida todos os campos previamente e empilha um único `CmdMacro` contendo os respectivos `CmdAlterarCampo`, permitindo desfazer a operação inteira em um único passo

#### Scenario: Adição e remoção em coleção repeated com geração de UID e retorno de tamanho
- **WHEN** o cliente MCP chama `aresta_adicionar_repeated` ou `aresta_remover_repeated`
- **THEN** o item é inserido (com `uid` NanoID válido gerado imediatamente) ou removido, e a resposta retorna o `uid`, o `caminho`, o `indice` e o `tamanho` atualizado da coleção

#### Scenario: Operações de mapas e imagens encapsuladas no Controller
- **WHEN** o cliente MCP invoca ferramentas de migração de setor, alteração de imagem/markdown ou vinculação de referências em mapas
- **THEN** o `CroquiController` ou `MapasController` executa os comandos canônicos (`CmdAlterarImagem`, `CmdAlterarAnexo`, `CmdAlterarCampo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`) agrupados em `CmdMacro` quando aplicável, preservando referências por `alvo_uid` e `pontos_uids`

### Requirement: Ferramentas de Visão, Inspeção de Coleções Repeated e Conhecimento (Proto e Skills)
O servidor MCP MUST disponibilizar ferramentas que permitam ao agente:
1. Capturar o viewport gráfico ativo (`aresta_capturar_canvas`) em PNG Base64;
2. Inspecionar a árvore ou qualquer sub-alvo/campo (`aresta_obter_arvore`), incluindo o tamanho explícito de todas as coleções `repeated` (`tamanhos_repeated`) e a leitura direta de campos `repeated` sem erro de serialização;
3. Consultar o esquema Protobuf `croqui.proto` e a estrutura detalhada de mensagens/enums com comentários de documentação (`aresta_obter_esquema_proto`);
4. Listar e ler as *skills* do repositório (`aresta_listar_skills` e `aresta_ler_skill`).

#### Scenario: Captura de tela do canvas ativo
- **WHEN** o cliente MCP invoca a ferramenta `aresta_capturar_canvas`
- **THEN** o sistema captura o frame renderizado do viewport solicitado e retorna o bloco de imagem codificado em PNG Base64 compatível com modelos multimodais

#### Scenario: Inspeção de mensagem com tamanhos de coleções repeated e leitura direta de campo repeated
- **WHEN** o cliente MCP consulta `aresta_obter_arvore` informando um `alvo` (e opcionalmente um `campo`, inclusive uma lista `repeated`)
- **THEN** o sistema retorna os dados em JSON junto ao mapa `tamanhos_repeated` (informando o comprimento atual de cada coleção `repeated` da mensagem, mesmo quando `0`) ou, se `campo` for uma coleção `repeated`, retorna `{"tamanho": N, "itens": [...]}`

#### Scenario: Consulta ao esquema Protobuf e às skills do domínio
- **WHEN** o cliente MCP invoca `aresta_obter_esquema_proto` (com ou sem `tipo_mensagem`), `aresta_listar_skills` ou `aresta_ler_skill`
- **THEN** o sistema retorna a definição estruturada de campos, tipos, `oneofs`, valores de `Enum` e docstrings do `croqui.proto`, ou a lista e o conteúdo completo das *skills* orientadas ao uso do MCP

### Requirement: Controle do Ciclo de Vida do Projeto e Workspace
O servidor MCP MUST disponibilizar ferramentas para consultar o status do workspace, disparar a compilação e validação do croqui, manipular o histórico (`desfazer`/`refazer`), focar elementos na interface e salvar no disco.

#### Scenario: Validação e compilação do croqui
- **WHEN** o cliente MCP chama a ferramenta `aresta_compilar`
- **THEN** o compilador do Aresta é executado sobre o estado atual e retorna o status de sucesso junto à lista estruturada de erros ou advertências

#### Scenario: Foco por UID e sincronização visual da interface
- **WHEN** o cliente MCP invoca `aresta_focar_elemento` passando o `uid` ou caminho de um setor, grupo, escalada ou mapa
- **THEN** a interface gráfica do editor seleciona e destaca visualmente o elemento correspondente para o usuário
