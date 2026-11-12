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
O servidor MCP primário MUST ser iniciado logo na abertura da `TelaDeCarregamento` do Editor Aresta (mesmo sem croqui aberto) e MUST ser mantido em execução contínua na mesma porta e sessão durante toda a vida útil da aplicação, inclusive nas transições entre `TelaDeCarregamento` e `JanelaPrincipal` e de volta via "Abrir Novo". A inicialização do servidor HTTP/Uvicorn em segundo plano MUST NOT bombear eventos da interface gráfica (`processEvents`) na thread principal do Qt. O servidor MUST expor `aresta_listar_croquis`, `aresta_abrir_croqui_existente`, `aresta_importar_croqui_oficial`, `aresta_criar_novo_croqui` e `aresta_particionar_pdf_croqui`. Quando nenhum croqui estiver aberto, qualquer ferramenta de inspeção ou mutação de croqui MUST retornar erro descritivo orientando o agente a abrir ou criar um croqui antes.

#### Scenario: Listagem de croquis abertos, em andamento e oficiais sem croqui aberto
- **WHEN** o Editor Aresta está na `TelaDeCarregamento` (sem croqui aberto) e o cliente MCP chama `aresta_listar_croquis`
- **THEN** o servidor já ativo responde imediatamente com as listas `abertos` (`[]`), `experimentais` (rascunhos locais) e `oficiais` (repositório de produção filtrável por `filtro`)

#### Scenario: Abertura ou criação de croqui a partir da Tela de Carregamento
- **WHEN** o Editor Aresta está na `TelaDeCarregamento` (com o servidor MCP ativo na porta primária) e o usuário pela interface gráfica ou o cliente MCP abre, importa ou cria um croqui
- **THEN** o aplicativo fecha a `TelaDeCarregamento`, abre a `JanelaPrincipal` reutilizando a mesma instância e porta do `ServidorMCP` (sem reiniciar o servidor HTTP nem derrubar conexões ativas), atualiza o estado para `croqui_aberto=True` com o `id_croqui` carregado e registra as ferramentas de edição do croqui

#### Scenario: Retorno à Tela de Carregamento preservando o Servidor MCP ativo
- **WHEN** o usuário aciona "Abrir Novo" na `JanelaPrincipal` para voltar à `TelaDeCarregamento`
- **THEN** a `JanelaPrincipal` fecha sem encerrar o `ServidorMCP` compartilhado, que volta ao estado `croqui_aberto=False` na mesma porta e continua respondendo às ferramentas globais de gestão de croquis

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

### Requirement: Migração Atômica de Escalada entre Setores via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_migrar_escalada` para mover uma `Escalada` de um `Setor` de origem para um `Setor` de destino em um único `CmdMacro`, resolvendo automaticamente o setor e o índice de origem a partir de `alvo_escalada` (UID ou caminho), preservando o `uid` da escalada, suas imagens em RAM e suas referências em mapas, e reindexando `IndiceUidsModel`.

#### Scenario: Migração de escalada entre setores informando apenas UID da escalada e UID do setor de destino
- **WHEN** o cliente MCP chama `aresta_migrar_escalada` informando `alvo_escalada` (UID da escalada) e `alvo_setor_destino` (UID ou caminho do setor de destino, com `indice_destino` opcional)
- **THEN** o servidor localiza automaticamente o setor de origem e o índice atual da escalada, executa `CroquiController.migrar_escalada` empilhando um único `CmdMacro` (`CmdRemoverRepeated` + `CmdAdicionarRepeated`), atualiza `IndiceUidsModel` e retorna `uid`, `setor_origem`, `indice_origem`, `setor_destino` e `indice_destino`

#### Scenario: Rejeição defensiva ao migrar alvo que não é uma Escalada ou setor inválido
- **WHEN** o cliente MCP chama `aresta_migrar_escalada` passando um `alvo_escalada` inexistente ou que não pertença à coleção `escaladas` de um `Setor`, ou um `alvo_setor_destino` inválido
- **THEN** o servidor MCP lança erro antes de empilhar qualquer comando na `QUndoStack` e retorna `isError: True` com mensagem descritiva

### Requirement: Alteração Multi-Alvo em Lote via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_alterar_em_lote` que recebe uma lista não vazia `operacoes` (onde cada item define `alvo` e `campo`/`valor` ou `campos`), valida e coage todos os alvos e valores previamente (*fail-fast*) e despacha todas as mutações em um único `CmdMacro` atômico na pilha de histórico.

#### Scenario: Atualização atômica de múltiplas entidades distintas em uma única chamada MCP
- **WHEN** o cliente MCP chama `aresta_alterar_em_lote` passando `operacoes` com alterações em múltiplos `UID`s ou caminhos (incluindo campos primitivos, enums por nome, variantes `oneof`, submensagens e listas `repeated`)
- **THEN** o servidor coage todos os valores para seus tipos Protobuf, empilha um único `CmdMacro` via `CroquiController.alterar_em_lote`, reindexa `IndiceUidsModel` ao final e retorna a quantidade total de operações e alvos alterados, permitindo reverter todo o lote com um único `undo()`

#### Scenario: Atomicidade fail-fast quando uma operação do lote é inválida
- **WHEN** o cliente MCP chama `aresta_alterar_em_lote` com uma lista `operacoes` na qual qualquer item possui `alvo` inexistente, campo desconhecido ou valor incompatível com o `FieldDescriptor`
- **THEN** a chamada falha antes de executar ou empilhar qualquer subcomando na `QUndoStack`, mantendo o `CroquiModel` integralmente inalterado

### Requirement: Omissão de Extensões e Campos Protobuf Invisíveis na Árvore e no Esquema MCP
As ferramentas `aresta_obter_arvore` e `aresta_obter_esquema_proto` MUST omitir chaves de extensão Protobuf iniciadas por `"[aresta."` (como `ext_metadados_arquivo`) e todos os campos marcados no `croqui.proto` com `(aresta.formato_na_ui) = INVISIVEL` ou `(aresta.mensagem_formato_na_ui) = INVISIVEL`, preservando visíveis exclusivamente os identificadores de endereçamento `uid`, `alvo_uid` e `pontos_uids`.

#### Scenario: Omissão de ext_metadados_arquivo e campos INVISIVEL em aresta_obter_arvore preservando UIDs
- **WHEN** o cliente MCP chama `aresta_obter_arvore` em um croqui contendo extensões `[aresta.ArquivoSetor.ext_metadados_arquivo]`, campos `precomputados`, `malha_estrada`, `arquivos_externos`, `ultima_migracao`, `curadoria_betas`, `compilado` e campos legados de referência (`id`, `ids`, `escalada`, `setor`, `grupo`)
- **THEN** o dicionário retornado em `dados` e `tamanhos_repeated` omite recursivamente todas essas chaves e extensões, mas preserva integralmente os campos `uid`, `alvo_uid` e `pontos_uids` em todas as mensagens

#### Scenario: Omissão de campos e tipos INVISIVEL em aresta_obter_esquema_proto preservando UIDs
- **WHEN** o cliente MCP chama `aresta_obter_esquema_proto` (com ou sem `tipo_mensagem`)
- **THEN** a definição estruturada das mensagens omite os campos internos/depreciados marcados como `INVISIVEL` (como `precomputados`, `malha_estrada`, `compilado` e campos legados de `Referencia`), mantendo documentados os campos `uid`, `alvo_uid` e `pontos_uids`

### Requirement: Listagem Tabular de Escaladas Cruzadas com Referências de Mapas
O servidor MCP MUST disponibilizar a ferramenta `aresta_listar_escaladas` (aceitando `alvo_setor` e `filtro_nome` opcionais) que percorre setores, grupos e mapas do croqui (incluindo `mapas_gerais`) e retorna uma lista compacta das escaladas enriquecida com `uid`, `indice_no_setor`, `setor_uid`, `setor_nome`, `rotulos_mapa`, `pontos_uids`, `tipo`, `nome`, `dificuldade`, `data_abertura` e `conquistadores`.

#### Scenario: Listagem de todas as escaladas do croqui com rótulos de mapa resolvidos
- **WHEN** o cliente MCP chama `aresta_listar_escaladas` sem filtros (ou filtrando por `alvo_setor` / `filtro_nome`)
- **THEN** o servidor cruza os `alvo_uid` das `referencias` de todos os mapas dos setores e de `mapas_gerais` com os `pontos_de_interesse` correspondentes e retorna a lista de escaladas contendo seus respectivos `rotulos_mapa` e `pontos_uids`

### Requirement: Inserção em Lote e Retorno Explícito de UIDs Gerados em Coleções Repeated
A ferramenta `aresta_adicionar_repeated` MUST aceitar tanto `valor` (item único) quanto `valores` (lista de itens inseridos atomicamente em um único `CmdMacro`) e MUST retornar explicitamente os campos `uid`, `uid_gerado` (quando 1 item for inserido) e `uids_gerados` (lista com os UIDs gerados na ordem de inserção), além do índice inicial inserido e do tamanho final da coleção.

#### Scenario: Adição de item único ou múltiplos itens em lista repeated com retorno de UIDs gerados
- **WHEN** o cliente MCP chama `aresta_adicionar_repeated` passando `valor` (1 item) ou `valores` (lista de N itens) para uma coleção de mensagens com `uid` (como `escaladas` ou `pontos_de_interesse`)
- **THEN** todos os itens recebem `uid` NanoID válido, são inseridos atomicamente no `CroquiModel` (em um único passo de `undo()` quando em lote), o `IndiceUidsModel` é atualizado e o retorno JSON inclui `uids_gerados` (e `uid_gerado` quando unitário)

### Requirement: Remoção Seletiva ou Integral de Referências de Mapa via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_remover_referencia_mapa` (apoiada por `MapasController.remover_referencia`) para desvincular pontos específicos (`pontos_uids`) de uma `Referencia` de `alvo_uid` em um `Mapa` ou remover a entrada `Referencia` inteira quando `pontos_uids` for omitido ou quando todos os seus pontos forem removidos.

#### Scenario: Desvinculação seletiva de pontos ou remoção integral de referência em um mapa
- **WHEN** o cliente MCP chama `aresta_remover_referencia_mapa` informando `alvo_mapa`, `alvo_uid` e opcionalmente `pontos_uids`
- **THEN** se `pontos_uids` contiver apenas parte dos pontos vinculados ao `alvo_uid`, o sistema atualiza a `Referencia` mantendo os pontos restantes via `CmdAlterarCampo`; se `pontos_uids` for omitido ou esvaziar todos os pontos da `Referencia`, o sistema remove a entrada `Referencia` via `CmdRemoverRepeated`

### Requirement: Preservação Opt-In de Campos Compatíveis na Troca de Variante Oneof via MCP
As ferramentas `aresta_alterar_campo` e `aresta_alterar_em_lote` MUST aceitar o parâmetro booleano opcional `preservar_campos_compativeis` (padrão `False`). Quando `preservar_campos_compativeis=True` e a mutação alterar a variante ativa de um `oneof` de submensagem, o sistema MUST copiar os campos homônimos compatíveis já preenchidos da variante anterior antes de aplicar os novos valores fornecidos.

#### Scenario: Conversão de modalidade de escalada com preservar_campos_compativeis ativado
- **WHEN** uma `Escalada` do tipo `via_esportiva` (com `nome`, `dificuldade`, `conquistadores`, `data_abertura` e `descricao` preenchidos) é alterada para `via_movel` via `aresta_alterar_campo` ou `aresta_alterar_em_lote` com `preservar_campos_compativeis=True`
- **THEN** a nova submensagem `via_movel` herda automaticamente todos os campos homônimos compatíveis da `via_esportiva` anterior, sobrescrevendo apenas os campos explicitamente informados na chamada, e um único `undo()` restaura a `via_esportiva` original

#### Scenario: Conversão de modalidade de escalada com preservar_campos_compativeis padrão (False)
- **WHEN** o cliente altera a variante de um `oneof` sem informar `preservar_campos_compativeis` (ou com `preservar_campos_compativeis=False`)
- **THEN** a nova submensagem da variante contém apenas os campos explicitamente enviados na chamada, mantendo o comportamento padrão do Protobuf

### Requirement: Coleta Assíncrona de Betas em Background via MCP com Persistência Incremental por Micro-Lote
O servidor MCP MUST disponibilizar a ferramenta `aresta_coletar_betas` para gerenciar a coleta multi-fonte de candidatos a beta (`acao`: `"iniciar"`, `"status"` ou `"cancelar"`). A execução das buscas de rede MUST ocorrer integralmente fora da thread principal da interface gráfica (Qt Event Loop), despachando para a thread principal exclusivamente a leitura inicial das escaladas e a gravação atômica de cada micro-lote concluído no histórico (`QUndoStack`) via `CroquiController`. A ferramenta MUST suportar filtragem opcional por `alvo_setor`, `escaladas_uids` e `apenas_sem_coleta` (padrão `True`, ignorando escaladas que já possuam entrada em `curadoria_betas.conteudo` ou betas aprovados), além de *long-polling* limitado por `aguardar_segundos` (máximo `20.0s`) fora da thread principal do Qt, retornando sempre um resumo estruturado leve sem despejar as listas completas de candidatos ou rejeitados.

#### Scenario: Coleta completa rápida dentro da janela de long-polling
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", aguardar_segundos=15)` para um conjunto de escaladas cuja busca termina antes do tempo limite de espera
- **THEN** o servidor executa a busca multi-fonte fora da thread principal do Qt, grava os novos candidatos em `betas_nao_scorados` e os itens auto-filtrados em `betas_rejeitados` via `CroquiController` e retorna imediatamente na mesma chamada `status: "concluido"` com os contadores `total_escaladas`, `escaladas_processadas`, `novos_candidatos_adicionados` e `novos_rejeitados_adicionados`

#### Scenario: Coleta de grande porte (1.000+ vias) com retorno parcial e persistência incremental por micro-lote
- **WHEN** o cliente MCP inicia uma coleta para um croqui com centenas ou milhares de escaladas que excede `aguardar_segundos` e depois consulta `aresta_coletar_betas(acao="status")` ou solicita `aresta_coletar_betas(acao="cancelar")`
- **THEN** a chamada retorna `status: "em_andamento"` dentro do limite de `aguardar_segundos` sem bloquear a UI nem estourar o timeout da ponte MCP, cada micro-lote concluído em segundo plano é gravado incrementalmente em `curadoria_betas.conteudo` via `CroquiController`, e caso a coleta seja cancelada, todo o progresso dos micro-lotes já processados permanece preservado no modelo

#### Scenario: Filtragem automática de escaladas já coletadas com apenas_sem_coleta ativado
- **WHEN** o cliente MCP chama `aresta_coletar_betas(acao="iniciar", apenas_sem_coleta=True)` em um croqui onde parte das escaladas já possui entrada em `curadoria_betas.conteudo` (com candidatos ou rejeitados) ou betas publicados em `Escalada.betas`
- **THEN** o sistema ignora as escaladas já coletadas e executa as buscas web exclusivamente para as escaladas ainda sem coleta registrada

### Requirement: Listagem Paginada e Enriquecida de Betas Não Scorados via MCP
O servidor MCP MUST disponibilizar a ferramenta `aresta_listar_betas_nao_scorados` (aceitando `offset`, `limite` e `alvo_setor` opcionais) que retorna apenas as escaladas que possuem itens pendentes em `betas_nao_scorados`, enriquecidas com os metadados da escalada (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_uid`, `setor_nome`, `pico_nome`, `conquistadores`, `betas_nao_scorados`, `betas_nao_revisados`) e omitindo a lista `betas_rejeitados`.

#### Scenario: Paginação de escaladas com betas_nao_scorados em croqui de grande porte
- **WHEN** o cliente MCP chama `aresta_listar_betas_nao_scorados(offset=0, limite=20)` em um croqui contendo centenas de escaladas e milhares de itens em `betas_rejeitados`
- **THEN** o servidor retorna `total_escaladas_pendentes`, `total_candidatos_pendentes`, `offset`, `limite`, `tem_mais` e a fatia de até 20 itens contendo os metadados de cada escalada e sua lista `betas_nao_scorados`, sem incluir `betas_rejeitados` no payload JSON
