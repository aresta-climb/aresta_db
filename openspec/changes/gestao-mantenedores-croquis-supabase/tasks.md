## 1. Migrações e Modelo de Dados no Supabase (Princípios II, III e IV)

- [ ] 1.1 Criar migração SQL com tabelas `mantenedores_croquis` e `mantenedores_auditoria`, chaves estrangeiras, índices e triggers de auditoria em `supabase/migrations/` e verificar aplicação bem-sucedida do schema no banco de testes
- [ ] 1.2 Definir políticas de Row Level Security (RLS) nas tabelas garantindo isolamento de leitura/escrita para usuários comuns e privilégios totais apenas para administradores e verificar conformidade através de testes de acesso RLS

## 2. Testes de Integração e Edge Functions no Backend (Princípios I, II, III, IV e V)

- [ ] 2.1 Criar teste de integração de fronteira cobrindo o fluxo de solicitação, aprovação administrativa e validação de mantenedor em `supabase/functions/integracao_governanca_mantenedores_test.ts` e verificar falha inicial (Red)
- [ ] 2.2 Implementar biblioteca desacoplada `servico_mantenedores.ts` para validação de escopo de arquivos modificados na PR via TDD com 100% de cobertura em `servico_mantenedores_test.ts`
- [ ] 2.3 Implementar Edge Function `consultar-mantenedores` para listar mantenedores ativos de um determinado croqui via TDD com 100% de cobertura em `index_test.ts`
- [ ] 2.4 Implementar Edge Function `aprovar-sugestao-pr` que valida se o usuário autenticado é mantenedor do croqui alterado e emite aprovação no GitHub via GitHub App Token via TDD com 100% de cobertura em `index_test.ts`

## 3. Integração no Repositório e Validação do CI/CD (Princípios I, III, IV e V)

- [ ] 3.1 Criar teste unitário e de integração para o despachante de integração de PRs em `tests/integracao_aprovacao_mantenedor_test.py` simulando aprovação via Bot vs aprovação global de dev via TDD com 100% de cobertura
- [ ] 3.2 Atualizar o workflow `.github/workflows/pr-integrator.yml` para reconhecer e processar aprovações emitidas pelo GitHub App em nome de mantenedores locais autorizados e verificar execução dos jobs
- [ ] 3.3 Executar validação de conformidade com `pr_db_validator.py` e testes de regressão do repositório para assegurar ausência de dados pessoais e integridade das pipelines
