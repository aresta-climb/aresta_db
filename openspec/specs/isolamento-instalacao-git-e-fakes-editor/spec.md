# isolamento-instalacao-git-e-fakes-editor Specification

## Purpose
Garantir que o Editor Aresta possa ser executado e testado de ponta a ponta em completo isolamento local dentro de diretórios temporários (`tmp_path`), utilizando repositórios Git locais reais e bibliotecas `test-only` de Fakes determinísticos para todas as fronteiras de nuvem e sistema operacional.

## Requirements

### Requirement: Redirecionamento Completo dos Diretórios da Instalação para `tmp_path`
A biblioteca de armazenamento (`editor/core/storage.py`) SHALL permitir redirecionar o diretório base da instalação (`aresta_db`, `croquis`, `diarios_locais` e `.trash_interna`) através de parâmetro explícito em `GerenciadorCaminhos` ou da variável de ambiente `ARESTA_DIRETORIO_DADOS`.

#### Scenario: Isolamento de pastas via variável de ambiente em testes
- **WHEN** a variável de ambiente `ARESTA_DIRETORIO_DADOS` aponta para um diretório temporário `tmp_path`
- **THEN** qualquer chamada a `obter_diretorio_base_app()` ou instância padrão de `GerenciadorCaminhos()` SHALL resolver todas as pastas da instalação dentro de `tmp_path`, sem tocar nos diretórios reais do usuário no sistema operacional.

### Requirement: Configuração de Upstream Git Local para Sincronização Sem Rede
O `GerenciadorSincronizacao` (`editor/core/sync.py`) SHALL permitir sobrescrever a URL oficial do repositório remoto através da variável de ambiente `ARESTA_GIT_UPSTREAM_URL` ou parâmetro explícito, viabilizando `clonar()`, `configurar_remotes()`, `fazer_fetch()` e `fazer_checkout_main_upstream()` contra um repositório Git local em `tmp_path`.

#### Scenario: Clone e fetch reais a partir de repositório Git local em `tmp_path`
- **WHEN** `ARESTA_GIT_UPSTREAM_URL` aponta para um repositório Git inicializado em `tmp_path/remoto_oficial.git` contendo a branch `main`
- **THEN** a `TarefaInicializacao` SHALL clonar e fazer fetch dos objetos Git diretamente do caminho local usando `pygit2`, concluindo a sincronização sem realizar conexões de rede.

### Requirement: Bibliotecas `test-only` de Fakes Determinísticos para Fronteiras Externas
O sistema SHALL prover bibliotecas de Fakes determinísticos em memória (cada qual acompanhada de seu arquivo `_fake_test.py` espelhado) para autenticação Supabase, sessão/cofre de credenciais, submissão/sincronização de PRs, servidor de conexão com celular e adaptador de plataforma.

#### Scenario: Simulação determinística de autenticação, sessão e atualização da loja
- **WHEN** `ClienteAuthSupabaseFake`, `GerenciadorSessaoFake` e `AdaptadorPlataformaFake` são injetados no ciclo de inicialização e login
- **THEN** os fluxos de envio/validação de OTP, leitura/gravação de sessão sem cofre do SO, edição de perfil de autor e aviso de atualização SHALL operar inteiramente em memória, suportando simulação determinística de sucesso e erro.

#### Scenario: Simulação de publicação e conflito de Pull Request em `ServicoSubmissaoFake`
- **WHEN** `ServicoSubmissaoFake` é acionado pela `JanelaPrincipal` ou pelo `PublishController`
- **THEN** ele SHALL calcular os arquivos modificados comparando com o repositório Git local em `tmp_path` e simular a criação/atualização de PR e o retorno de `ATUALIZADO`, `MESCLADO` ou `CONFLITO` (acionando o `DialogoConflitoSincronizacao`) sem acessar a rede.

#### Scenario: Simulação de pareamento e Live Reload em `ServidorCelularFake`
- **WHEN** o usuário ou robô aciona a conexão com celular na `JanelaPrincipal` com `ServidorCelularFake` configurado
- **THEN** o Fake SHALL fornecer porta, código de pareamento, URL de prévia e imagem de QR Code em memória sem abrir sockets para `8.8.8.8` ou `previa.arestaclimb.com`, permitindo emitir `dispositivo_conectado` e registrar notificações de `emitir_recarregamento`.

### Requirement: Injeção de Dependências de Fronteira no Ciclo de Vida do Editor
As classes `ControladorAplicativo`, `TarefaInicializacao` e `JanelaPrincipal` SHALL aceitar a injeção opcional das instâncias ou fábricas de fronteira externa (`servico_submissao`, `fabrica_servidor_celular`, `cliente_auth`, `gerenciador_sessao` e `servico_loja`), utilizando as implementações de produção por padrão quando omitidas.

#### Scenario: Propagação de Fakes da janela principal para fluxos filhos
- **WHEN** `JanelaPrincipal` é instanciada com `servico_submissao` e `fabrica_servidor_celular` injetados
- **THEN** as ações de publicar croqui, sincronizar PR remota e conectar ao celular SHALL utilizar as dependências injetadas em vez de instanciar clientes de rede concretos.

### Requirement: Isolamento Global Automático de Cofre de Credenciais e Diretório de Dados na Suíte de Testes
A infraestrutura global de testes (`conftest.py`) e a biblioteca `editor/core/gerenciador_sessao_fake.py` SHALL garantir que nenhuma execução do `pytest` acesse ou modifique o cofre de credenciais real do sistema operacional (`WinVaultKeyring`, `macOS.Keyring`, `SecretService`, `KWallet`) nem o diretório de dados real do usuário (`%APPDATA%/Editor Aresta` ou equivalente).

#### Scenario: Backend de Keyring determinístico em memória ativo por padrão em todos os testes
- **WHEN** qualquer teste da suíte é executado pelo `pytest`
- **THEN** uma fixture `autouse=True` no `conftest.py` SHALL instalar uma instância limpa de `CofreChaveiroFake` (backend de `keyring` 100% em memória) e redirecionar `ARESTA_DIRETORIO_DADOS` para um diretório temporário isolado
- **AND** chamadas diretas ou indiretas a `GerenciadorSessao()`, `keyring.get_password()`, `keyring.set_password()` ou `keyring.delete_password()` SHALL operar exclusivamente sobre o `CofreChaveiroFake` em memória e sobre o diretório temporário do teste, preservando intacta qualquer sessão real do desenvolvedor

#### Scenario: Simulação determinística de falhas de cofre via `CofreChaveiroFake`
- **WHEN** um teste configura `CofreChaveiroFake` para simular erro de leitura, escrita ou remoção de senha
- **THEN** o backend em memória SHALL lançar a exceção configurada de forma determinística sem necessidade de `unittest.mock.patch` sobre funções globais do módulo `keyring`
