## Why

Atualmente, a publicação de alterações no Aresta Editor depende de permissões diretas de escrita no repositório `aresta-climb/aresta_db` ou de um fluxo de forks que falha para usuários da comunidade (erro 403 por limitações de escopo de GitHub Apps e falta de instalação em contas pessoais). 

Para resolver isso de forma definitiva, segura e com mínima fricção, implementaremos a infraestrutura de backend no repositório dedicado `../aresta_backend` (Supabase Edge Functions) que unifica o fluxo de publicação para todos os usuários (mantenedores e comunidade), atuando como um Git Proxy com Firewall e automatizando a criação de Pull Requests com um Bot, sem expor permissões elevadas nem exigir forks na conta pessoal dos contribuidores. O sistema utilizará o Supabase Auth com login por código de e-mail (OTP de 6 dígitos) integrado ao serviço transacional Resend, coletando e associando o nome do autor ao seu perfil para a atribuição oficial nos commits e Pull Requests.

## What Changes

- Criação da Supabase Edge Function `git-proxy` em `../aresta_backend/supabase/functions/git-proxy/`:
  - Intercepta requisições Git Smart HTTP (`/info/refs` e `/git-receive-pack`).
  - Autenticação via JWT do Supabase Auth (obtendo e-mail, identificador de usuário e nome do autor extraído dos metadados).
  - Firewall de Branch: Permite push exclusivamente para branches no padrão `refs/heads/sugestao-[a-zA-Z0-9_-]+$`, rejeitando tentativas para `main` ou qualquer outro padrão com HTTP 403.
  - Verificação de Conflito em Novas Branches: Se o push for para criar uma nova branch (`old_oid` nulo), valida se a branch ainda não existe no repositório remoto.
  - Verificação de Propriedade em Atualizações: Se o push for para atualizar uma branch `sugestao-*` existente, valida se o autor atual possui o mesmo e-mail do autor original da sugestão registrado no Supabase.
  - Streaming Bidirecional: Faz streaming do payload Git em tempo real para `github.com/aresta-climb/aresta_db.git` injetando credenciais seguras de Bot (GitHub App Installation Token / Bot Token).
- Criação da Supabase Edge Function `create-pr` em `../aresta_backend/supabase/functions/create-pr/`:
  - Endpoint REST autenticado via JWT para formalização de Pull Request.
  - Validação de Escopo de Pastas: Inspeciona o diff da branch `sugestao-*` e garante que **apenas** arquivos dentro do diretório `database/` foram modificados. Caso existam alterações fora dessa pasta, a branch é removida e a requisição é rejeitada com HTTP 400.
  - Abertura da Pull Request no GitHub com a identidade do Bot e atribuição detalhada ao autor (nome completo e e-mail).
- Tabela de controle no Supabase (`sugestoes_branches`) via migração SQL em `../aresta_backend/supabase/migrations/` para mapeamento de branches, autores, nomes e Pull Requests associadas.
- Guia de configuração do Supabase Auth com provedor de e-mail OTP via Resend (SMTP e Templates).
- Aplicação rigorosa dos `PRINCIPIOS.md`: código 100% em português brasileiro, desenvolvimento Library-First em módulos desacoplados em `../aresta_backend/supabase/functions/compartilhado/`, TDD com ciclo Red-Green-Refactor, testes de integração prévios e 100% de cobertura de testes unitários.

## Capabilities

### New Capabilities
- `backend-git-proxy`: Proxy inteligente para Git Smart HTTP que valida autenticação JWT, atua como firewall de branch (`sugestao-*`), garante a inexistência de colisão em novas branches, valida propriedade em atualizações e injeta token de Bot para streaming com o GitHub.
- `backend-pr-api`: Serviço REST para validação de escopo de diretório (`database/` restrito), captura de metadados do autor (nome e e-mail) e abertura automatizada de Pull Requests no repositório oficial via Bot.

### Modified Capabilities
<!-- Nenhuma especificação de cliente desktop é modificada neste sub-projeto de backend -->

## Impact

- **Repositório Alvo / Infraestrutura**: Implementação no repositório `../aresta_backend` (Deno/TypeScript Edge Functions no Supabase e tabela de rastreamento no PostgreSQL).
- **Autenticação e E-mail**: Utiliza Supabase Auth configurado com Resend para envio de e-mails transacionais (OTP).
- **GitHub**: Requer configuração de segredos de GitHub App / Bot Token no ambiente Supabase do `aresta_backend`.
- **Segurança**: Elimina a necessidade de concessão de escopos de escrita em contas pessoais de usuários, bloqueia modificações fora de `database/` e protege a branch `main` contra pushes diretos.
