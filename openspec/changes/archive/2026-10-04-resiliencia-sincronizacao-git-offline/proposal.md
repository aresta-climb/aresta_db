# Proposal

## Why

Atualmente, quando o Editor Aresta inicia, ele tenta realizar um `fetch` nos remotes Git do repositório base (`aresta_db`). Em ambientes com instabilidade de rede, atrasos de firewall corporativo ou falhas transitórias de conexão segura (SSL/WinHTTP no Windows), o `pygit2`/`libgit2` esgota o tempo de retransmissão TCP (~21 segundos) e dispara uma exceção críptica `GitError: no error`.

Como o fluxo de inicialização não possui tratamento resiliente nem modo de degradação suave (fallback offline), qualquer falha no `fetch` encerra imediatamente a aplicação inteira com `QApplication.quit()`, mesmo nos casos em que o repositório local já existe no disco (`%appdata%\EditorAresta\aresta_db`) com todos os croquis e mapas utilizáveis. Além disso, credenciais de usuário expiradas são enviadas desnecessariamente para leitura de repositório público, e o retorno de credenciais nulas causa erros internos no `pygit2`.

Esta alteração é necessária para garantir resiliência operacional, permitindo que o editor continue funcionando em modo offline quando a sincronização remota falhar, e fornecendo mensagens de erro compreensíveis caso a máquina realmente não consiga realizar o download inicial obrigatório.

## What Changes

- **Modo offline e degradação suave na inicialização (`worker.py`)**: Se o repositório base já existir localmente no disco, uma falha na chamada `fazer_fetch` ou `fazer_checkout_main_upstream` não interrompe o arranque do editor; a falha é registrada como aviso (`logger.warning`), a interface visual notifica o estado offline e a inicialização prossegue com os dados locais.
- **Tratamento e tradução de erros crípticos no Git (`sync.py`)**: Criação da exceção `ErroSincronizacaoGit`. Captura de `pygit2.GitError` convertendo a mensagem `"no error"` para um diagnóstico claro de rede/tempo limite/SSL.
- **Correção no callback de credenciais (`sync.py`)**: Substituição do retorno `None` por `raise pygit2.Passthrough()` quando o token for nulo, aderindo ao contrato de callbacks do `pygit2`.
- **Desacoplamento de token de usuário para leituras públicas (`worker.py` e `sync.py`)**: Não propagar `sessao.token_github` (que pode expirar) nas operações de leitura de repositório público (`clonar`, `fazer_fetch`), reservando tokens estritamente para submissões autenticadas.
- **Eliminação de fetch duplicado (`sync.py`)**: Deduplicar remotes apontando para a mesma URL em `fazer_fetch`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade necessária; o comportamento é uma evolução direta das capacidades existentes. -->

### Modified Capabilities
- `editor-sincronizacao-git`: Adição de requisito de resiliência e degradação graciosa em falhas de rede durante o `fetch`, e sanitização do tratamento de credenciais públicas.
- `editor-inicializacao`: Adição de requisito para que falhas não críticas de sincronização remota não encerrem a aplicação se houver dados locais pré-existentes.

## Impact

- **Código Afetado**:
  - `editor/core/sync.py`: Tratamento de exceções, criação de `ErroSincronizacaoGit`, uso de `pygit2.Passthrough` e deduplicação de remotes.
  - `editor/core/worker.py`: Resiliência em `TarefaInicializacao` com fallback offline e remoção de token de usuário no sync de leitura pública.
  - `editor/core/sync_test.py`: Atualização dos testes unitários garantindo 100% de cobertura.
  - `editor/core/worker_test.py`: Novos cenários de teste simulando falha de fetch com continuidade da aplicação e falha no primeiro clone com erro bloqueante.
- **Dependências e Sistemas**:
  - Nenhuma nova dependência externa necessária (`pygit2` existente é mantido).
