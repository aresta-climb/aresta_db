# Spec Delta

## MODIFIED Requirements

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
