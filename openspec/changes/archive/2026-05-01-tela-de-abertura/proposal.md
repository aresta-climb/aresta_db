## Por que

Atualmente, o Editor Aresta abre diretamente na página inicial sem garantir que o ambiente local esteja sincronizado ou que o usuário esteja autenticado. Precisamos de uma Splash Screen para realizar processos pesados (como clone/pull de repositórios) e garantir a identidade do autor antes de permitir edições, melhorando a experiência do usuário e a integridade dos dados.

## O que muda

- **Nova Tela de Abertura (Splash Screen)**: Uma janela inicial animada (em Português) que bloqueia o acesso à Janela Principal até que a inicialização termine.
- **Autenticação GitHub**: Implementação do fluxo de dispositivo (Device Flow) para autenticação segura.
- **Armazenamento Seguro de Tokens**: Uso da biblioteca `keyring` para persistir o token do GitHub.
- **Sincronização Robusta**: Uso de `pygit2` para operações Git, com suporte a repositórios privados da organização `aresta-climb/aresta_db` e forks automáticos.
- **Feedback Visual Aprimorado**: Barra de progresso estilizada (exibida apenas durante sync) e instruções de autenticação detalhadas com suporte a múltiplas linhas.
- **Arquitetura em Português**: Refatoração completa de classes e variáveis para seguir o `PRINCIPIOS.md` (ex: `TelaDeAbertura`, `TarefaInicializacao`).

## Capacidades

### Novas Capacidades
- `editor-inicializacao`: Gerenciamento do ciclo de vida da `TelaDeAbertura` e verificação de saúde do storage local.
- `editor-autenticacao`: Fluxo de login via GitHub Device Flow e gestão de credenciais locais via `keyring`.
- `editor-sincronizacao-git`: Lógica de clone/fork/pull usando `pygit2` com injeção de token para repositórios privados.

### Capacidades Modificadas
- `editor-arquitetura`: Atualização para incluir a `TelaDeAbertura` no fluxo de inicialização e a mudança de dependência de `gitpython` para `pygit2`.

## Impacto

- **Dependências**: Adição de `pygithub`, `pygit2` e `keyring`.
- **Arquitetura**: O ponto de entrada (`main.py`) orquestra a `TelaDeAbertura` e trata erros de inicialização (como falta de permissão em repositórios privados).
- **Storage**: O repositório local agora é salvo na pasta `aresta_db` dentro do AppData do usuário.
