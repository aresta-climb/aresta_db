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
O servidor MCP MUST expor ferramentas mapeadas à interface canônica de `CroquiController` e `MapasController`, aceitando endereçamento híbrido por `UID` universal (`IndiceUidsModel`), `<uid>.<subcaminho>` ou caminho posicional. A ferramenta `aresta_alterar_campo` MUST suportar tanto a alteração de um único campo quanto de um dicionário `campos` em lote (agrupado internamente em um `CmdMacro` pelo `CroquiController`), convertendo automaticamente dicionários JSON em submensagens Protobuf (ou variantes `oneof`), nomes de `Enum` em seus valores inteiros correspondentes, e listas JSON em substituição declarativa completa de campos `repeated` (removendo itens anteriores e adicionando os novos dentro do mesmo `CmdMacro`, preservando `uid`s fornecidos e gerando NanoIDs para novos itens). O servidor MCP MUST NOT expor ferramentas manuais de abertura/fechamento de macro (`iniciar_macro`/`finalizar_macro`) nem ferramentas de desfazer/refazer (`aresta_desfazer`/`aresta_refazer`).

#### Scenario: Alteração unificada de campo primitivo, indexado, oneof, submensagem ou enum por nome
- **WHEN** o cliente MCP chama `aresta_alterar_campo` informando o `alvo` (UID ou caminho) e um `campo` + `valor` (seja primitivo, `campo.0`, variante `oneof` como `via_esportiva`, submensagem como `dict` ou `Enum` por string como `"BR_7A"`)
- **THEN** a camada MCP converte o JSON para o tipo Protobuf correspondente, despacha via `CroquiController.alterar_campo` executando `CmdAlterarCampo` no histórico e retorna o estado atualizado

#### Scenario: Alteração atômica de múltiplos campos em lote no mesmo alvo
- **WHEN** o cliente MCP chama `aresta_alterar_campo` informando `alvo` (ex: `UID` de um `Setor` ou `Mapa`) e um dicionário `campos` contendo campos escalares e listas `repeated` (ex: `escaladas`, `mapas` ou `pontos_de_interesse`)
- **THEN** o `CroquiController` valida todos os campos e itens previamente e empilha um único `CmdMacro` contendo os respectivos `CmdAlterarCampo`, `CmdRemoverRepeated` e `CmdAdicionarRepeated`, substituindo a subárvore inteira de forma atômica e preservando `uid`s existentes

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
O servidor MCP MUST disponibilizar ferramentas para consultar o status do workspace (`aresta_status_workspace`), disparar a compilação e validação do croqui (`aresta_compilar`), focar elementos na interface (`aresta_focar_elemento`) e salvar no disco (`aresta_salvar`), sem expor comandos de desfazer/refazer aos agentes.

#### Scenario: Validação e compilação do croqui
- **WHEN** o cliente MCP chama a ferramenta `aresta_compilar`
- **THEN** o compilador do Aresta é executado sobre o estado atual e retorna o status de sucesso junto à lista estruturada de erros ou advertências

#### Scenario: Foco por UID e sincronização visual da interface
- **WHEN** o cliente MCP invoca `aresta_focar_elemento` passando o `uid` ou caminho de um setor, grupo, escalada ou mapa
- **THEN** a interface gráfica do editor seleciona e destaca visualmente o elemento correspondente para o usuário

### Requirement: Ativação na Tela de Seleção, Gestão de Croquis e Guarda sem Croqui Aberto
O servidor MCP MUST ser iniciado logo na abertura do Editor Aresta (inclusive quando o aplicativo estiver apenas na `TelaDeCarregamento`, sem croqui aberto). O servidor MUST expor `aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui` e `aresta_particionar_pdf_croqui`. Quando nenhum croqui estiver aberto, qualquer ferramenta de inspeção ou mutação de croqui MUST retornar erro descritivo orientando o agente a abrir ou criar um croqui antes.

#### Scenario: Listagem de croquis abertos, em andamento e oficiais sem croqui aberto
- **WHEN** o Editor Aresta está na `TelaDeCarregamento` (sem croqui aberto) e o cliente MCP chama `aresta_listar_croquis`
- **THEN** o servidor retorna as listas `abertos` (`[]`), `em_andamento` (rascunhos locais) e `oficiais` (repositório de produção filtrável por `busca`)

#### Scenario: Abertura ou criação de croqui a partir da Tela de Carregamento
- **WHEN** o Editor Aresta está na `TelaDeCarregamento` e o cliente MCP chama `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial` ou `aresta_criar_novo_croqui`
- **THEN** o aplicativo fecha a `TelaDeCarregamento`, abre a `JanelaPrincipal` com o croqui solicitado e retorna os metadados da sessão aberta (`id_croqui`, `uid_croqui`, `caminho_database`)

#### Scenario: Guarda defensiva ao chamar ferramentas de edição sem croqui aberto
- **WHEN** nenhum croqui está aberto no Editor Aresta e o cliente MCP chama uma ferramenta dependente de modelo (como `aresta_obter_arvore`, `aresta_alterar_campo`, `aresta_renderizar_mapa`, `aresta_compilar` ou `aresta_salvar`)
- **THEN** o servidor MCP retorna `isError: True` com mensagem orientando a usar `aresta_listar_croquis` e uma das ferramentas de abertura/criação de croqui

#### Scenario: Particionamento de PDF e pré-alocação de esqueletos com UIDs no croqui
- **WHEN** o cliente MCP chama `aresta_particionar_pdf_croqui` informando `caminho_pdf` e o dicionário `partes` em um croqui aberto
- **THEN** o sistema extrai os sub-PDFs, imagens `.webp` e metadados vetoriais via `PyMuPDF`, cria na árvore Protobuf os esqueletos ausentes (`Botao`, `Setor`, `Grupo`, `ColecaoDeMapas`) com `UID`s NanoID válidos (preservando os `UID`s existentes em caso de atualização) e retorna o mapeamento `parte -> {uid, caminho_pdf, imagens}`

### Requirement: Suporte a Múltiplas Janelas por Croqui e Roteamento Proxy MCP
O Editor Aresta MUST substituir a trava global de instância única por uma trava escopada por croqui (`ArestaEditorCroqui_<id_croqui>`), permitindo múltiplas janelas abertas simultaneamente em croquis distintos. Cada instância MUST registrar sua porta e `id_croqui` em `mcp_sessoes.json`. O servidor MCP na porta principal `27378` MUST aceitar o parâmetro opcional `id_croqui` em todas as ferramentas de croqui e encaminhar transparentemente via proxy local as chamadas destinadas a outras janelas abertas.

#### Scenario: Abertura de um segundo croqui enquanto outro já está aberto
- **WHEN** a Janela #1 já está aberta com o croqui `"A"` e o cliente MCP chama `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial` ou `aresta_criar_novo_croqui` para um croqui `"B"` diferente de `"A"`
- **THEN** a Janela #1 permanece aberta com `"A"`, uma nova janela independente é aberta para `"B"`, registrada em `mcp_sessoes.json`, e seus dados são retornados ao cliente

#### Scenario: Tentativa de abrir novamente um croqui que já está aberto
- **WHEN** o croqui `"A"` já está aberto em uma janela ativa e o cliente MCP ou o usuário solicita abrir `"A"` novamente
- **THEN** o sistema não cria uma segunda janela duplicada, ativa a janela existente de `"A"` e retorna os dados da sessão já aberta

#### Scenario: Roteamento proxy transparente por id_croqui na porta 27378
- **WHEN** há múltiplas janelas abertas (`"A"` na porta `27378` e `"B"` na porta `27379`) e o cliente MCP envia uma chamada na porta `27378` informando `id_croqui="B"`
- **THEN** o servidor na porta `27378` encaminha a requisição JSON-RPC para a porta `27379` e retorna a resposta ao cliente; se `id_croqui` for omitido havendo mais de um croqui aberto, retorna erro listando os `id_croqui` abertos

### Requirement: Renderização de Mapa com Grade Métrica e Recortes de POIs em Lista Intercalada
O servidor MCP MUST disponibilizar a ferramenta `aresta_renderizar_mapa` para inspecionar mapas sem dependência de `PaddleOCR`. A ferramenta MUST retornar uma sequência intercalada de blocos `[Texto, Imagem]` no array `content`: primeiro o bloco de texto com metadados (`largura`, `altura`, candidatos vetoriais extraídos pelo `PyMuPDF`) seguido da imagem completa do mapa com grade métrica semitransparente (`100px`), réguas graduadas nas bordas (`X`/`Y`) e POIs atuais desenhados em vermelho; em seguida, pares `[Texto, Imagem]` para cada POI com seu `uid`, `rotulo`, coordenadas atuais e o recorte ampliado (`120x120px`) com mira central `(0,0)` e eixos relativos (`-50px` a `+50px`).

#### Scenario: Renderização de mapa com grade métrica e recortes individuais de POIs
- **WHEN** o cliente MCP chama `aresta_renderizar_mapa` passando o `alvo` de um `Mapa` que possui pontos de interesse
- **THEN** a resposta MCP retorna múltiplos itens intercalados de texto e imagem PNG Base64, começando pela visão geral com grade/réguas e seguindo com um par `[Texto descritivo do POI, Imagem de recorte com mira relativa]` para cada ponto de interesse
