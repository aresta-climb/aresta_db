## 1. Banco de Dados e Modelagem (em `../aresta_backend/supabase/migrations/`)

- [ ] 1.1 Criar migração SQL `../aresta_backend/supabase/migrations/20260823000000_criar_tabela_sugestoes_branches.sql` com a tabela `sugestoes_branches` (incluindo colunas `author_name`, `author_email`) e índices de unicidade
- [ ] 1.2 Configurar permissões de Service Role e políticas RLS para proteção dos registros de sugestões

## 2. Testes de Integração e Contratos de Fronteira (Primeiro Passo)

- [ ] 2.1 Criar suite de testes de integração em `../aresta_backend/supabase/functions/` para o fluxo Git Smart HTTP (simulando requisições `/info/refs` e `/git-receive-pack`)
- [ ] 2.2 Criar suite de testes de integração em `../aresta_backend/supabase/functions/` para o endpoint `create-pr` (simulando payloads válidos com nome/e-mail, inválidos e com violação de pasta)

## 3. Bibliotecas Compartilhadas (TDD: Red-Green-Refactor, 100% Cobertura em `../aresta_backend`)

- [ ] 3.1 Criar testes em `../aresta_backend/supabase/functions/compartilhado/analisador_pkt_line_test.ts` e implementar `analisador_pkt_line.ts` para parsing e validação de comandos Git
- [ ] 3.2 Criar testes em `../aresta_backend/supabase/functions/compartilhado/validador_regras_branch_test.ts` e implementar `validador_regras_branch.ts` para validação de regex (`sugestao-*`) e bloqueio de `main`
- [ ] 3.3 Criar testes em `../aresta_backend/supabase/functions/compartilhado/validador_escopo_arquivos_test.ts` e implementar `validador_escopo_arquivos.ts` para validação restrita da pasta `database/`
- [ ] 3.4 Criar testes em `../aresta_backend/supabase/functions/compartilhado/cliente_supabase_controle_test.ts` e implementar `cliente_supabase_controle.ts` para persistência e consulta de propriedade de branch e metadados do autor (nome e e-mail)
- [ ] 3.5 Criar testes em `../aresta_backend/supabase/functions/compartilhado/cliente_github_bot_test.ts` e implementar `cliente_github_bot.ts` para operações com Octokit (comparação de arquivos, criação de PR formatada com nome do autor e exclusão de branch)

## 4. Edge Function `git-proxy` (TDD e Orquestração em `../aresta_backend`)

- [ ] 4.1 Criar testes em `../aresta_backend/supabase/functions/git-proxy/index_test.ts`
- [ ] 4.2 Implementar orquestrador em `../aresta_backend/supabase/functions/git-proxy/index.ts` integrando autenticação JWT, extração de nome/e-mail do autor, firewall e streaming para o GitHub
- [ ] 4.3 Validar 100% de cobertura de testes unitários no módulo `git-proxy` (`deno test --coverage`)

## 5. Edge Function `create-pr` (TDD e Orquestração em `../aresta_backend`)

- [ ] 5.1 Criar testes em `../aresta_backend/supabase/functions/create-pr/index_test.ts`
- [ ] 5.2 Implementar orquestrador em `../aresta_backend/supabase/functions/create-pr/index.ts` com validação de escopo e abertura de PR via Bot contendo atribuição do autor
- [ ] 5.3 Validar 100% de cobertura de testes unitários no módulo `create-pr` (`deno test --coverage`)

## 6. Validação Geral e Documentação de Setup

- [ ] 6.1 Executar a suite completa de testes em `../aresta_backend` com verificação de 100% de cobertura (`deno test --coverage`)
- [ ] 6.2 Executar a suite completa de testes de integração validando todos os cenários
- [ ] 6.3 Documentar o guia passo a passo de configuração do Supabase Auth com SMTP do Resend e variáveis de ambiente (`GITHUB_BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) no README do `aresta_backend`
