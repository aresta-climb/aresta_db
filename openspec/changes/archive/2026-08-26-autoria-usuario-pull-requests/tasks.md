## 1. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 1.1 Atualizar teste de integração `aresta_backend/supabase/functions/integracao_create_pr_test.ts` adicionando cenário de criação de PR com `token_usuario_github` e cenário de fallback para o bot em caso de token inválido
- [x] 1.2 Atualizar teste de integração `editor/core/integracao_submissao_proxy_test.py` verificando a propagação de `sessao.token_github` até o payload de submissão do PR

## 2. Backend: Autoria Dinâmica e Fallback em `create-pr` via TDD (Princípios I, II, III e IV)

- [x] 2.1 Criar testes unitários em `aresta_backend/supabase/functions/compartilhado/cliente_github_bot_test.ts` para `criarPullRequestGithub` com `tokenUsuarioGithub` e fallback para o bot
- [x] 2.2 Implementar suporte a `tokenUsuarioGithub?: string` em `cliente_github_bot.ts` com captura de erro e fallback para `obterInstanciaOctokit()`
- [x] 2.3 Criar testes unitários em `aresta_backend/supabase/functions/create-pr/index_test.ts` para extração de `token_usuario_github` / `github_user_token` do corpo da requisição
- [x] 2.4 Implementar extração e repasse de `token_usuario_github` em `create-pr/index.ts`
- [x] 2.5 Validar 100% de cobertura no backend com `deno test -A` e realizar o deploy de `create-pr` no Supabase

## 3. Desktop: Biblioteca de Submissão e Escopo OAuth via TDD (Princípios I, II, III e IV)

- [x] 3.1 Criar testes unitários em `editor/core/servico_submissao_test.py` para `solicitar_abertura_pr` e `submeter_sugestao` verificando envio de `token_usuario_github`
- [x] 3.2 Implementar suporte a `token_usuario_github` em `solicitar_abertura_pr` e `submeter_sugestao` em `editor/core/servico_submissao.py`
- [x] 3.3 Criar testes unitários em `editor/views/tela_de_abertura_test.py` validando que a URL de autorização OAuth do GitHub contém o escopo `public_repo`
- [x] 3.4 Atualizar `iniciar_login_github` em `editor/views/tela_de_abertura.py` para incluir `public_repo` nos scopes (`read:user,user:email,public_repo`)

## 4. Validação Geral e 100% de Cobertura (Princípio III)

- [x] 4.1 Executar a suíte completa de testes (`pytest`) no `aresta_db` e garantir 100% de cobertura nos módulos modificados

