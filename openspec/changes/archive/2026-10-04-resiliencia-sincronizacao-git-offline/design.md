# Design

## Context

Ver `proposal.md` para contexto e motivação. O Editor Aresta utiliza `pygit2` para gerenciar a cópia local do banco de dados oficial (`aresta_db`) no diretório `%appdata%\EditorAresta\aresta_db`. Durante a inicialização na thread em segundo plano (`TarefaInicializacao` em `editor/core/worker.py`), o editor verifica se a pasta existe e, se existir, invoca `sync.fazer_fetch()` e `sync.fazer_checkout_main_upstream()`.

No Windows, o transporte HTTPS do `pygit2` é implementado pela `libgit2` sobre a API do WinHTTP. Em caso de instabilidade de rede ou falha de conexão, as tentativas internas esgotam após ~21 segundos (timeout SYN TCP) e o `libgit2` limpa o estado de erro, gerando a exceção críptica `GitError: no error`. Sem tratamento de contingência, a aplicação encerra bruscamente mesmo com todos os dados locais intactos.

## Goals / Non-Goals

**Goals:**
- Permitir que o editor abra normalmente e opere em modo offline caso a sincronização remota falhe e a base local de croquis já exista no disco.
- Converter exceções opacas do Git (`GitError: no error`) em diagnósticos legíveis de conexão/rede via `ErroSincronizacaoGit`.
- Corrigir o contrato de callbacks de credenciais no `pygit2` lançando `pygit2.Passthrough()` quando não houver token.
- Desacoplar tokens de sessão de usuário de operações de leitura em repositórios públicos.
- Garantir 100% de cobertura de testes unitários conforme os Princípios de Engenharia Aresta (`AGENTS.md`).

**Non-Goals:**
- Não alterar o fluxo de submissão de pull requests via proxy (`ServicoSubmissao`), que já opera de forma independente e com autenticação dedicada.
- Não introduzir sincronizador em tempo real ou rotina periódica em segundo plano durante a edição de croquis.
- Não depender de comandos do executável `git.exe` no sistema operacional.

## Decisions

### 1. Degradação Suave no Arranque do Worker (`worker.py`)
- **Decisão**: Envolver as etapas de `fazer_fetch` e `fazer_checkout_main_upstream` em um bloco `try/except` específico quando o repositório base local já estiver presente no disco.
- **Comportamento**: Em caso de exceção (`ErroSincronizacaoGit`, `pygit2.GitError` ou erro de conexão), registrar `logger.warning(...)`, emitir status `"Não foi possível conectar ao GitHub. Operando em modo offline..."` e permitir que a thread continue o fluxo normal até a conclusão (`self.progresso.emit(100)`, `self.sucesso.emit()`).
- **Alternativas consideradas**:
  - *Interromper e pedir confirmação*: Piora a experiência de uso para escaladores em campo ou conexões lentas.
  - *Timeout agressivo via threading/kill*: Complexo, arrisca corromper o índice do Git (`.git/index.lock`).

### 2. Exceção de Domínio `ErroSincronizacaoGit` em `sync.py`
- **Decisão**: Encapsular operações de rede em `sync.py` para capturar `pygit2.GitError`. Se o texto do erro for `"no error"`, formatar a mensagem: `"Tempo limite esgotado ou falha de conexão segura (SSL) ao conectar com o GitHub."`.
- **Justificativa**: Respeita o princípio *Library-First*. O consumidor da biblioteca (`worker.py`) recebe uma exceção limpa e informativa, sem necessidade de interpretar particularidades do WinHTTP.
- **Alternativas consideradas**:
  - *Interpretar a string no worker*: Acopla detalhes do `pygit2` na camada de coordenação da UI.

### 3. Contrato de Credenciais com `pygit2.Passthrough`
- **Decisão**: No método `credentials` de `ChamadasGit`, quando `self.token` for `None`, lançar `raise pygit2.Passthrough()` em vez de `return None`.
- **Justificativa**: O `pygit2` exige que uma classe que implementa `RemoteCallbacks` lance `Passthrough` para declinar o fornecimento de credenciais. Retornar `None` gera `TypeError: credential does not implement interface`.
- **Alternativas consideradas**:
  - *Retornar tupla vazia*: Rejeitado pelo `pygit2`.

### 4. Leituras Públicas sem Token de Usuário
- **Decisão**: Na inicialização do `GerenciadorSincronizacao` pelo `worker.py`, não repassar o `token_github` da sessão do usuário para operações de leitura pública da base `aresta_db`.
- **Justificativa**: O repositório oficial é público. Tokens OAuth de usuário podem expirar ou ter escopos restritos, gerando falhas espúrias em operações que não exigem privilégios.

### 5. Deduplicação de Remotes no Fetch
- **Decisão**: Em `fazer_fetch()`, filtrar a lista de remotes para evitar consultar duas vezes URLs idênticas (como `origin` e `upstream` ambos apontando para `https://github.com/aresta-climb/aresta_db.git`).

## Risks / Trade-offs

- **[Risco: Usuário editar croqui baseado em versão desatualizada da base]** → *Mitigação*: O editor opera com versionamento por arquivo e o `ServicoSubmissao` valida a branch no proxy antes de aceitar submissões. Ao conectar à internet, o próximo arranque puxará a versão mais recente.
- **[Risco: Primeira execução em máquina limpa sem internet]** → *Mitigação*: Se o repositório ainda não existir no disco, a falha do `clonar()` continua sendo tratada como erro crítico, exibindo mensagem amigável instruindo o usuário a conectar-se à internet para o download inicial.
