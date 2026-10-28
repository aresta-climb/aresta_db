# Spec Delta: editor-controle-mcp

## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Controle do Ciclo de Vida do Projeto e Workspace
O servidor MCP MUST disponibilizar ferramentas para consultar o status do workspace (`aresta_status_workspace`), disparar a compilação e validação do croqui (`aresta_compilar`), focar elementos na interface (`aresta_focar_elemento`) e salvar no disco (`aresta_salvar`), sem expor comandos de desfazer/refazer aos agentes.

#### Scenario: Validação e compilação do croqui
- **WHEN** o cliente MCP chama a ferramenta `aresta_compilar`
- **THEN** o compilador do Aresta é executado sobre o estado atual e retorna o status de sucesso junto à lista estruturada de erros ou advertências

#### Scenario: Foco por UID e sincronização visual da interface
- **WHEN** o cliente MCP invoca `aresta_focar_elemento` passando o `uid` ou caminho de um setor, grupo, escalada ou mapa
- **THEN** a interface gráfica do editor seleciona e destaca visualmente o elemento correspondente para o usuário
