## Context

Veja `proposal.md` para a motivação e contexto do problema. Atualmente, os mantenedores locais de croquis não possuem contas no GitHub e se autenticam exclusivamente pelo Aresta Editor via Supabase Auth (E-mail OTP). O GitHub `CODEOWNERS` nativo não aceita e-mails desvinculados de contas do GitHub, e armazenar e-mails no repositório git público geraria riscos inaceitáveis de spam e infração de privacidade (LGPD).

## Goals / Non-Goals

**Goals:**
- **Modelo de Dados e Auditoria no Supabase:** Estruturar `mantenedores_croquis` e `mantenedores_auditoria` com RLS estrito e rastreabilidade completa de concessão e revogação.
- **Governança por Devs Globais:** Interface e endpoints para que os administradores do Aresta avaliem e aprovem solicitações de mantenedores locais com visibilidade de seus nomes completos e e-mails reais no backend privado.
- **Aprovação Delegada via GitHub App:** Edge Function que recebe intenção de aprovação de um mantenedor autenticado no Supabase, valida a responsabilidade sobre o croqui e emite aprovação oficial no GitHub através do GitHub App do Aresta.
- **Preservação de Aprovação Global:** Manter inalterada a capacidade dos desenvolvedores do Aresta (`OWNER`, `MEMBER`, `COLLABORATOR`) de aprovar diretamente qualquer PR via GitHub.

**Non-Goals:**
- Criação de sistema de `@username` ou handles públicos para usuários.
- Armazenamento de qualquer dado pessoal ou UUID de mantenedor dentro dos arquivos `croqui.yaml` ou no repositório `aresta_db`.
- Visual Diff gráfico detalhado de croquis (reservado para o Sub-projeto 5).

## Decisions

### 1. Governança 100% no Supabase vs Arquivo no Git
- **Decisão:** Manter os registros de mantenedores exclusivamente no PostgreSQL do Supabase, sem espelhamento de dados pessoais ou UUIDs no Git.
- **Racional:**
  - O repositório Git público é alvo de indexação e scraping; expor e-mails é risco de privacidade e spam.
  - Colocar UUIDs opacos no Git resultaria em revisões cegas nos PRs de governança (os revisores não saberiam a identidade real por trás de `usr_3fa85f64...`).
  - No Supabase, o fluxo de aprovação de mantenedores é auditável, seguro e apresenta contexto humano completo (Nome e E-mail) para os administradores.
- **Alternativas descartadas:**
  - *E-mails no `croqui.yaml`:* Rejeitado por violação de privacidade (LGPD) e risco de spam.
  - *Arquivo raiz `config/mantenedores.yaml` com UUIDs:* Rejeitado por opacidade nas revisões e complexidade desnecessária de sincronização.

### 2. Validação Estrita de Escopo da Pull Request
- **Decisão:** Para que a aprovação de um mantenedor local seja aceita, a Pull Request deve modificar exclusivamente arquivos pertencentes aos croquis sob sua responsabilidade (`database/<croqui_autorizado>/**`).
- **Racional:** Impede que um mantenedor local de um croqui específico aprove acidentalmente ou maliciosamente alterações em outros croquis ou em códigos globais do repositório (ex: scripts, workflows, editor).
- **Tratamento de PRs de múltiplos croquis ou código:** Se o PR tocar em arquivos fora do escopo do mantenedor, a aprovação deve ser realizada obrigatoriamente por um desenvolvedor global do Aresta.

### 3. Emissão de Review pelo GitHub App
- **Decisão:** A Edge Function `aprovar-sugestao-pr` utiliza as credenciais do GitHub App (`BOT_APP_ID` e chave privada) para registrar a aprovação oficial no GitHub via API REST (`pull_request_review` com evento `APPROVE` ou comentário `/approve`).
- **Racional:** Usuários sem conta no GitHub não possuem tokens pessoais de API; o GitHub App atua como autoridade delegada confiável do projeto.

## Risks / Trade-offs

- **[Tentativa de aprovação cruzada não autorizada]** → Mitigação: A Edge Function obtém os arquivos modificados na PR diretamente da API do GitHub e cruza com a lista de `croqui_id` autorizados do usuário autenticado no banco com RLS/Service Role.
- **[Indisponibilidade do Supabase]** → Mitigação: Os desenvolvedores globais do Aresta continuam com acesso nativo para aprovar e fazer merge de PRs diretamente na interface do GitHub.
- **[Revogação de mantenedor]** → Mitigação: Atualizações de status para `revogado` na tabela `mantenedores_croquis` têm efeito imediato na Edge Function, bloqueando instantaneamente novas aprovações.
