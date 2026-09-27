## Why

Atualmente, croquis de escalada no repositório `aresta_db` não possuem uma forma descentralizada de definir pessoas responsáveis (mantenedores locais) por aprovar atualizações e sugestões da comunidade. O recurso nativo de `CODEOWNERS` do GitHub exige contas cadastradas e verificadas no GitHub.com para cada mantenedor, o que cria alta fricção para escaladores locais que utilizam apenas o Aresta Editor e se autenticam por e-mail OTP (Supabase). Além disso, expor e-mails ou dados pessoais em arquivos de texto no repositório git público geraria riscos severos de privacidade (LGPD) e spam via web scraping.

Armazenar e governar a relação de mantenedores 100% no Supabase, com auditoria completa de aprovações/revogações por administradores e integração com o GitHub App/Bot do Aresta, resolve a governança distribuída de croquis mantendo a privacidade total dos dados e preservando a supervisão global dos desenvolvedores do Aresta.

## What Changes

- **Governança de Mantenedores no Supabase (`aresta_backend`):**
  - Criação da tabela `mantenedores_croquis` vinculando `croqui_id` ao `usuario_id` com status (`pendente`, `ativo`, `revogado`), datas e identificação de quem aprovou/revogou.
  - Criação da tabela de auditoria `mantenedores_auditoria` para registro imutável do histórico de concessão e revogação de acessos.
  - Regras de segurança a nível de linha (RLS) garantindo que usuários possam solicitar manutenção e consultar seus próprios status, enquanto apenas administradores (devs globais do Aresta) podem aprovar ou revogar permissões.
  - Edge Functions seguras para solicitação, aprovação administrativa e consulta de mantenedores autorizados para um determinado croqui.
- **Validação de Aprovação via Bot no GitHub (`aresta_db`):**
  - Atualização do fluxo de integração (`pr-integrator.yml` / webhook) para validar se uma solicitação de aprovação emitida por um usuário do Supabase provém de um mantenedor ativo daquele croqui modificado.
  - Emissão de aprovação oficial ou comando `/approve` pelo GitHub App do Aresta quando o mantenedor local aprova a sugestão (via Editor ou link autenticado).
  - Preservação intacta da permissão global de merge para desenvolvedores do repositório (`OWNER`, `MEMBER`, `COLLABORATOR`).
- **Privacidade e Desacoplamento:**
  - Nenhuma informação de contato (e-mail, telefone) ou identificador interno de usuário é exposto nos arquivos `.yaml` ou `.md` do repositório público `aresta_db`.

## Capabilities

### New Capabilities
- `backend-governanca-mantenedores`: Modelo de dados, políticas RLS, tabela de auditoria e endpoints no Supabase para solicitação, aprovação e revogação de mantenedores de croquis por administradores.
- `integrador-aprovacao-mantenedor`: Fluxo de validação no CI/CD e GitHub App que reconhece a aprovação de mantenedores autenticados no Supabase e executa o merge de sugestões no GitHub, mantendo a permissão global dos devs do Aresta.

### Modified Capabilities
- `ci-cd-workflow-pr`: Atualizado para contemplar a validação de autorização de mantenedores via Supabase nas etapas de integração de Pull Requests.

## Impact

- **Backend Supabase (`aresta_backend`):**
  - Nova migração SQL criando `mantenedores_croquis` e `mantenedores_auditoria` com RLS.
  - Novas Edge Functions para gerenciar e validar mantenedores de croquis.
- **Repositório GitHub (`aresta_db`):**
  - Workflow `.github/workflows/pr-integrator.yml` expandido para suportar verificação de mantenedores via token de autorização emitido pelo backend.
- **Segurança & Privacidade:**
  - Conformidade estrita com LGPD: zero dados pessoais expostos em commits ou metadados de croquis públicos.
