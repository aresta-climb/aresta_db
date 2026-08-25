## 1. Testes de Integração em Primeiro Lugar e TDD (Princípios IV e V)

- [x] 1.1 Criar teste de integração de fronteira `editor/core/integracao_submissao_proxy_test.py` simulando o fluxo fim-a-fim de submissão via `pygit2` com repositórios locais e mocks do Supabase (Princípio V)
- [x] 1.2 Criar suite de testes unitários `editor/core/servico_submissao_test.py` com repositórios Git locais temporários (`tmp_path`) e fixtures de `SessaoUsuario`
- [x] 1.3 Implementar testes unitários para geração do nome da branch `sugestao-<id_croqui>-<uuid8>` e restrição de escopo de arquivos em `database/<id_croqui>/`
- [x] 1.4 Implementar testes unitários para criação de commit assinado com nome e e-mail do autor e mensagem formatada `sugestao(<id_croqui>): <titulo>`
- [x] 1.5 Implementar testes unitários para envio de push autenticado com JWT para o remote proxy (`RemoteCallbacks.credentials`)
- [x] 1.6 Implementar testes unitários para chamada HTTP REST da Edge Function `create-pr` cobrindo cenários de sucesso, validação e erro 4xx/5xx

## 2. Implementação da Biblioteca `ServicoSubmissao` (Library-First)

- [x] 2.1 Criar dataclass `ResultadoSubmissao` e classe `ServicoSubmissao` em `editor/core/servico_submissao.py`
- [x] 2.2 Implementar função `gerar_nome_branch(id_croqui: str) -> str` utilizando `uuid.uuid4().hex[:8]`
- [x] 2.3 Implementar método `sincronizar_arquivos_croqui(origem: Path, destino_repo: Path, id_croqui: str)` isolando alterações em `database/<id_croqui>/`
- [x] 2.4 Implementar método `criar_commit_sugestao(repo, branch, sessao, id_croqui, titulo, descricao)` com `pygit2.Signature` e mensagem estruturada
- [x] 2.5 Implementar método `fazer_push_proxy(repo, branch, jwt, url_proxy, callback_progresso)` com callbacks de progresso e autenticação
- [x] 2.6 Implementar método `solicitar_abertura_pr(url_supabase, chave_publica, jwt, branch, titulo, descricao)` disparando POST para `create-pr`
- [x] 2.7 Implementar fluxo de orquestração `submeter_sugestao(...)` com suporte a renovação silenciosa preventiva do JWT da sessão

## 3. Integração com `TarefaPublicacao`, `PublishController` e UI

- [x] 3.1 Refatorar `TarefaPublicacao` em `editor/core/worker.py` para consumir `ServicoSubmissao` e emitir progresso e status detalhados
- [x] 3.2 Atualizar testes unitários em `editor/core/worker_test.py`
- [x] 3.3 Adicionar checagens pré-envio no `PublishController` (validação de compilação limpa do croqui e detecção de diff real)
- [x] 3.4 Atualizar `PublishDialog` (`editor/views/publish_dialog.py`) para exibir o resumo dos arquivos modificados a serem transmitidos
- [x] 3.5 Atualizar testes em `editor/controllers/publish_controller_test.py`

## 4. Casos de Borda, Resiliência e Validação E2E

- [x] 4.1 Implementar tratamento de expiração irrecuperável de sessão no envio com diálogo em português e reinício seguro do login
- [x] 4.2 Implementar lógica de reaproveitamento de branch em PRs abertas e desvinculação automática quando a PR anterior estiver fechada/mergeada
- [x] 4.3 Executar a suíte completa de testes (`pytest`) garantindo 100% de aprovação e conformidade com `PRINCIPIOS.md`
