## Context

O Aresta Editor permite que autores editem croquis de escalada e publiquem alterações no repositório `aresta-climb/aresta_db`. Contudo, usuários sem permissão direta de escrita enfrentam falhas ao tentar criar forks automaticamente via GitHub App (erro 403 Forbidden).

Este documento de design estabelece a arquitetura da infraestrutura de backend implementada no repositório dedicado `../aresta_backend` (Supabase Edge Functions), aplicando rigorosamente todos os princípios de engenharia de software definidos em `PRINCIPIOS.md` e integrando autenticação OTP via Resend e captura de nome do autor.

## Alinhamento com os Princípios de Engenharia (PRINCIPIOS.md)

1. **I. Tudo em Português**: Todo o código-fonte (TypeScript/Deno), nomes de módulos, variáveis, funções, interfaces, comentários e testes são redigidos estritamente em português brasileiro (ex: `analisador_pkt_line.ts`, `validador_regras_branch.ts`, `processar_requisicao_git`).
2. **II. Library-First (Biblioteca em Primeiro Lugar)**: Toda a lógica é decomposta em bibliotecas modulares e autocontidas sob o diretório `../aresta_backend/supabase/functions/compartilhado/`. As Edge Functions (`index.ts`) funcionam apenas como orquestradores de entrada.
3. **III. 100% de Cobertura de Testes Unitários**: Cada biblioteca e endpoint possui 100% de cobertura de código verificável via `deno test --coverage`.
4. **IV. Imperativo do Teste em Primeiro Lugar (TDD)**: Todo arquivo `.ts` é acompanhado obrigatoriamente por seu arquivo `_test.ts` no mesmo diretório. O ciclo Vermelho-Verde-Refatorar é seguido para cada função.
5. **V. Testes de Integração em Primeiro Lugar**: Contratos de fronteira e fixtures de teste de integração (simulação de requisições Git Smart HTTP e chamadas REST com JWT) são estabelecidos antes do desenvolvimento das bibliotecas internas.
6. **VI. Simplicidade e Anti-Abstração**: Código declarativo e direto, sem camadas desnecessárias de classes ou padrões de fábrica complexos.

## Estrutura Modular Library-First (Repositório `../aresta_backend`)

```
../aresta_backend/
  supabase/
    migrations/
      20260823000000_criar_tabela_sugestoes_branches.sql
    functions/
      compartilhado/
        analisador_pkt_line.ts
        analisador_pkt_line_test.ts
        validador_regras_branch.ts
        validador_regras_branch_test.ts
        validador_escopo_arquivos.ts
        validador_escopo_arquivos_test.ts
        cliente_supabase_controle.ts
        cliente_supabase_controle_test.ts
        cliente_github_bot.ts
        cliente_github_bot_test.ts
      git-proxy/
        index.ts
        index_test.ts
      create-pr/
        index.ts
        index_test.ts
```

## Configuração do Supabase Auth com Resend (Guia de Setup)

Para o envio de códigos de autenticação (OTP de 6 dígitos) com alta entregabilidade, o Supabase Auth deve ser configurado com o serviço SMTP do **Resend**:

### 1. Obter Chave de API no Resend
1. Acesse o painel do [Resend](https://resend.com) e crie uma API Key com permissão de envio (`Full Access` ou `Sending Access`).
2. Em **Domains**, verifique o domínio oficial do projeto (`login.arestaclimb.com`) configurando os registros DNS (DKIM, SPF e MX). *Para desenvolvimento, pode-se usar o domínio de teste padrão do Resend*.

### 2. Configurar SMTP no Painel do Supabase
1. No painel do Supabase, navegue para **Project Settings → Authentication → SMTP Settings**.
2. Habilite a opção **Enable Custom SMTP**.
3. Preencha os campos com as credenciais do Resend:
   - **Sender Email**: `nao-responda@login.arestaclimb.com`
   - **Sender Name**: `Aresta Editor`
   - **Host**: `smtp.resend.com`
   - **Port**: `465` (com SSL) ou `587` (com TLS)
   - **User**: `resend`
   - **Password**: `<SUA_RESEND_API_KEY>`
4. Em **Authentication → Providers → Email**:
   - Habilite **Enable Email provider**.
   - Desmarque **Confirm email** se for usar login direto por OTP.
   - Em **Email Templates → Magic Link / OTP**, customize a mensagem:
     ```html
     <h2>Seu código de acesso ao Aresta Editor</h2>
     <p>Insira o código abaixo no aplicativo para continuar:</p>
     <h1 style="letter-spacing: 5px; font-size: 32px; color: #2b8a3e;">{{ .Token }}</h1>
     <p>Este código expira em 1 hora.</p>
     ```

### 3. Captura do Nome do Usuário nos Metadados
Ao autenticar via Supabase Auth, o cliente verifica se o usuário já possui o campo `nome_completo` nos metadados (`user.user_metadata.nome_completo`). Caso não possua (primeiro login):
1. O aplicativo exibe modal para coleta do nome do autor (ex: "Qual é o seu nome completo para registro nos croquis?").
2. O aplicativo atualiza os metadados do usuário via endpoint do Supabase Auth (`PUT /auth/v1/user` com `data: { "nome_completo": "Nome do Autor" }`).
3. O JWT passa a conter o nome verificado do autor, que é repassado automaticamente para o `git-proxy` e para a abertura da PR.

## Goals / Non-Goals

**Goals:**
- Implementar as bibliotecas compartilhadas e a Edge Function `git-proxy` (Deno/TypeScript) em `../aresta_backend/supabase/functions/`:
  - Parsing seguro de `pkt-line` do Git Smart HTTP (`/info/refs` e `/git-receive-pack`).
  - Firewall de branch: bloqueio estrito para referências fora de `^refs/heads/sugestao-[a-zA-Z0-9_-]+$`.
  - Verificação de colisão em novas branches (`old_oid` zeros).
  - Verificação de propriedade do autor original em atualizações.
  - Streaming transparente do payload para o GitHub injetando credenciais do Bot.
- Implementar as bibliotecas compartilhadas e a Edge Function `create-pr` (Deno/TypeScript) em `../aresta_backend/supabase/functions/`:
  - Validação de escopo de diretório: inspeciona o diff e garante que **apenas** arquivos em `database/` foram modificados.
  - Exclusão da branch de segurança e rejeição com HTTP 400 se arquivos fora de `database/` forem detectados.
  - Abertura automatizada da Pull Request no GitHub com a identidade do Bot e dados do autor (nome e e-mail).
- Modelar a tabela `sugestoes_branches` no PostgreSQL com RLS em `../aresta_backend/supabase/migrations/`.
- Suite completa de testes unitários (100% coverage) e testes de integração de fronteira executados no repositório `../aresta_backend`.

**Non-Goals:**
- Telas e controllers no cliente Desktop PyQt6 (escopo dos Sub-projetos 2 e 3).
- Painel de moderação e diff visual para mantenedores (escopo dos Sub-projetos 4 e 5).

## Decisions

### 1. Deno / TypeScript no repositório `../aresta_backend`
- **Decisão**: Toda a infraestrutura Serverless é desenvolvida e mantida dentro de `../aresta_backend/supabase/`.
- **Justificativa**: Centraliza toda a stack backend do Aresta Climb em um único repositório com CLI `supabase` configurado.

### 2. Streaming de Git Smart HTTP com Injeção de Bot Token
- **Decisão**: Fazer streaming direto do request/response com `TransformStream` do Deno, interceptando os primeiros bytes do stream para validar o comando sem buffering completo em disco.
- **Justificativa**: Performance máxima e capacidade de suportar commits pesados de fotos sem restrição de memória.

### 3. Validação de Escopo de Pastas via API de Comparação do GitHub
- **Decisão**: Inspecionar os arquivos alterados via endpoint de comparação do GitHub (`GET /repos/{owner}/{repo}/compare/main...{branch}`) dentro da função `create-pr`.
- **Justificativa**: Simplicidade e robustez máxima. Evita a complexidade de decodificar packfiles binários dentro do Deno.

### 4. Tabela de Controle de Propriedade (`sugestoes_branches`)
- **Decisão**: Tabela relacional no PostgreSQL indexando `branch_name` (UNIQUE), `author_id`, `author_email`, `author_name`, `pr_number`, `pr_url` e `status`.
- **Justificativa**: Validação determinística de propriedade e auditoria completa de sugestões com identificação nominal dos autores.

## Risks / Trade-offs

- **[Risco: Timeouts em pushes com muitas imagens]**  
  → **Mitigação**: Streaming HTTP chunked contínuo com keep-alive.
- **[Risco: Tentativa de adulteração de código fora de `database/`]**  
  → **Mitigação**: Exclusão sumária da branch remota e rejeição antes da abertura da PR.
- **[Risco: Exposição do Token do Bot]**  
  → **Mitigação**: Segredo armazenado exclusivamente como variável de ambiente no Supabase (`GITHUB_BOT_TOKEN`).
