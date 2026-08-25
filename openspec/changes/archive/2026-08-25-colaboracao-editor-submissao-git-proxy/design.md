## Context

O Aresta Editor Desktop permite a edição colaborativa de croquis de escalada. Com a infraestrutura de backend (Supabase Edge Functions `git-proxy` e `create-pr`) e o sistema de autenticação (OTP/OAuth com Envelope Encryption AES-256-GCM) concluídos, este documento detalha a arquitetura do cliente Desktop para a criação de branches, commits locais assinados com `pygit2`, push seguro via Git Smart HTTP através do proxy e abertura de Pull Requests automatizadas.

## Alinhamento com os Princípios de Engenharia (PRINCIPIOS.md)

1. **I. Tudo em Português**: Todo o código-fonte Python, nomes de classes (`ServicoSubmissao`, `ResultadoSubmissao`), métodos (`gerar_nome_branch`, `sincronizar_arquivos_croqui`, `criar_commit_sugestao`, `fazer_push_proxy`, `solicitar_abertura_pr`, `submeter_sugestao`), variáveis, mensagens de erro, diálogos e documentação são estritamente redigidos em português brasileiro.
2. **II. Library-First (Biblioteca em Primeiro Lugar)**: Toda a regra de negócio de criação de branch, empacotamento, commit assinado com `pygit2`, push HTTP para o proxy e requisições REST para `create-pr` reside na biblioteca autocontida `editor/core/servico_submissao.py`, sem dependências do framework de UI. A `TarefaPublicacao` e o `PublishController` funcionam apenas como orquestradores enxutos da interface.
3. **III. 100% de unit test coverage**: Todo o código novo desenvolvido possui 100% de cobertura de testes unitários automatizados, aferível via `pytest --cov`.
4. **IV. Imperativo do Teste em Primeiro Lugar (TDD)**: Todo arquivo `.py` é acompanhado de seu respectivo `_test.py` no mesmo diretório (`editor/core/servico_submissao_test.py`). O ciclo Vermelho-Verde-Refatorar é aplicado em cada tarefa de implementação.
5. **V. Testes de Integração em Primeiro Lugar**: O contrato de fronteira fim-a-fim da submissão é validado previamente através do arquivo de teste de integração `editor/core/integracao_submissao_proxy_test.py`, simulando repositórios Git reais criados em diretórios temporários (`tmp_path`) e respostas mockadas das Edge Functions do Supabase.
6. **VI. Simplicidade e Anti-Abstração**: Sem fábricas complexas, decorators desnecessários ou hierarquias artificiais de classes. Funções declarativas, modulares e reutilizáveis.
7. **VII. Edições de Estado via Comandos do Histórico (Undo/Redo)**: A submissão valida que o histórico do editor (`QUndoStack`) está salvo antes de prosseguir, garantindo que o estado visual e o arquivo persistido em disco estejam perfeitamente sincronizados.

## Goals / Non-Goals

**Goals:**
- Implementar a biblioteca desacoplada `editor/core/servico_submissao.py` (*Library-First*) responsável por:
  - Criação de branches locais temporárias no formato `sugestao-<id_croqui>-<uuid8>`.
  - Sincronização e isolamento de arquivos modificados em `database/<id_croqui>/`.
  - Criação de commits assinados via `pygit2.Signature` com o nome e e-mail da `SessaoUsuario`.
  - Configuração de remote efêmero e push autenticado para `https://<supabase>/functions/v1/git-proxy`.
  - Invocação da Edge Function `create-pr` via REST com envio de metadados.
- Criar a suite de testes `editor/core/servico_submissao_test.py` com 100% de cobertura, utilizando repositórios Git locais temporários (`tmp_path`) e mocks HTTP para a API do Supabase.
- Refatorar a `TarefaPublicacao` (`editor/core/worker.py`) e o `PublishController` (`editor/controllers/publish_controller.py`) para consumir a nova biblioteca e a `SessaoUsuario`.
- Implementar validações pré-envio locais (compilação limpa do croqui, detecção de diff real e resumo dos arquivos no diálogo).
- Tratar cenários de sessão expirada com renovação silenciosa de JWT antes do envio.

**Non-Goals:**
- Painel de moderação e listagem de PRs para mantenedores (escopo do Sub-projeto 4).
- Visual Diff e ações de Merge/Rejeição na UI (escopo do Sub-projeto 5).

## Decisions

### 1. Padrão de Nomenclatura da Branch: `sugestao-<id_croqui>-<uuid8>`
- **Decisão:** A branch de sugestão terá o formato `sugestao-<id_croqui>-<uuid8>`, onde `<uuid8>` são os primeiros 8 dígitos hexadecimais de `uuid.uuid4().hex[:8]`.
- **Alternativas consideradas:**
  - `sugestao-<id_croqui>-<timestamp>`: muito longo (~50 caracteres), prejudicando a visualização no terminal e na UI do GitHub.
  - `sugestao-<uuid8>`: muito curto, dificultando identificar qual croqui está sendo modificado na lista de branches do GitHub.
- **Vantagem:** Permite identificação instantânea do croqui alvo com garantia matemática de unicidade (4,29 bilhões de combinações por croqui).

### 2. Mensagem de Commit Padronizada com Assinatura do Autor
- **Decisão:** O commit gerado localmente pelo `pygit2` terá a mensagem:
  ```text
  sugestao(<id_croqui>): <Título fornecido pelo usuário>

  <Descrição fornecida pelo usuário>

  Signed-off-by: <Nome Completo do Autor> <<email>>
  ```
- **Vantagem:** Estrutura clara, rastreável no histórico Git e compatível com DCO (Developer Certificate of Origin).

### 3. Autenticação Git Smart HTTP com JWT via RemoteCallbacks
- **Decisão:** No momento do push via `pygit2`, o callback `RemoteCallbacks.credentials` fornecerá credenciais HTTP com o usuário `"bearer"` e a senha contendo o `jwt_supabase` da sessão.
- **Alternativas consideradas:**
  - Token do GitHub pessoal: descartado, pois colaboradores comuns autenticados via e-mail não possuem contas ou tokens do GitHub.
- **Vantagem:** O `git-proxy` valida o JWT e injeta as credenciais do Bot com segurança.

### 4. Ciclo de Vida da Sugestão e Atualização Contínua
- **Decisão:**
  - Se `croqui_experimental.yaml` contiver uma branch de PR aberta (`pull_request_branch`), o editor reutiliza a mesma branch no push.
  - O `git-proxy` autoriza o push validando que o e-mail do autor é o criador da branch.
  - Se a PR anterior estiver fechada ou aceita (merged), o vínculo é resetado e uma nova branch `sugestao-<id_croqui>-<uuid8>` é gerada.

### 5. Validações Pré-Envio Locais na Interface
- **Decisão:** O editor executa 3 verificações antes de liberar o push:
  1. *Compilação*: Valida se `croqui.yaml` compila sem erros.
  2. *Diff real*: Checa se há arquivos novos ou modificados em relação à `upstream/main`.
  3. *Resumo*: Exibe no `PublishDialog` a lista e a quantidade de arquivos que serão transmitidos (YAML e imagens).

### 6. Aproveitamento da Base Madura e Eliminação do PyGithub no Envio
- **Decisão:** Reutilizar integralmente a infraestrutura existente de Git e UI do editor:
  - O algoritmo de sincronização de diretórios (`sync_dir`), adição seletiva ao índice (`index.add_all`), verificação de árvore (`write_tree`) e persistência de metadados em `croqui_experimental.yaml`.
  - A interface com `PublishDialog`, `QProgressDialog` e `DialogoSucessoPR`.
  - **Eliminação do PyGithub:** Toda a dependência de `github.Github`, criação de forks pessoais e chamadas `g.create_pull` é removida do fluxo de submissão. O cliente passa a operar estritamente com `pygit2` (Git Smart HTTP) e `requests` (Edge Function `create-pr`), tornando o cliente leve, resiliente e sem dependência de credenciais pessoais de GitHub do autor.

## Risks / Trade-offs

- **[Token JWT expirado durante a submissão]** → *Mitigação*: `ServicoSubmissao` realiza renovação silenciosa preventiva do JWT via `ClienteAuthSupabase.renovar_sessao` antes de iniciar o push. Se a renovação falhar por expiração do refresh token, orienta salvar e reinicia o fluxo de login de forma segura.
- **[Queda de rede ou erro na Edge Function]** → *Mitigação*: Exibição de mensagem descritiva em português e preservação da branch e arquivos locais intactos, permitindo nova tentativa imediata com 1 clique.
- **[Conflito de arquivos fora do escopo `database/`]** → *Mitigação*: `ServicoSubmissao` restringe a cópia e o `index.add_all` estritamente ao diretório `database/<id_croqui>/`.
