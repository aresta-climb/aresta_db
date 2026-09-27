## Purpose

Provê o modelo de dados, políticas de segurança RLS, histórico de auditoria e endpoints no Supabase para gerenciar a solicitação, aprovação e revogação de mantenedores de croquis por administradores sem expor dados pessoais no repositório público.

## ADDED Requirements

### Requirement: Tabela de Mantenedores de Croquis
O banco de dados PostgreSQL do Supabase MUST manter o registro estruturado dos mantenedores vinculados a cada croqui, contendo o estado de aprovação e quem autorizou o vínculo.

#### Scenario: Estrutura da tabela mantenedores_croquis
- **WHEN** a tabela `mantenedores_croquis` for consultada no Supabase
- **THEN** ela MUST conter os campos `id` (UUID), `croqui_id` (texto identificador do croqui), `usuario_id` (UUID referenciando auth.users), `status` (`pendente`, `ativo`, `revogado`), `solicitado_em` (timestamp), `aprovado_em` (timestamp nulo até aprovação), `aprovado_por` (UUID do administrador) e `revogado_em` (timestamp opcional)

### Requirement: Políticas de Acesso RLS
O acesso aos registros de mantenedores MUST ser estritamente controlado por políticas de Row Level Security (RLS) no Supabase.

#### Scenario: Usuário comum consulta e solicita vínculos
- **WHEN** um usuário autenticado acessar a tabela `mantenedores_croquis`
- **THEN** ele MUST conseguir visualizar apenas seus próprios registros e criar novas solicitações com status inicial `pendente`
- **AND** ele MUST ser impedido de alterar o status para `ativo` ou modificar registros de outros usuários

#### Scenario: Administrador global aprova ou revoga vínculos
- **WHEN** um usuário com privilégios de administrador (dev global do Aresta) acessar a tabela `mantenedores_croquis`
- **THEN** ele MUST ter permissão para listar solicitações de todos os croquis e atualizar o status para `ativo` ou `revogado` preenchendo os campos de auditoria

### Requirement: Trilha de Auditoria Imutável de Mantenedores
O sistema MUST manter um registro histórico de auditoria para cada alteração de concessão, recusa ou revogação de mantenedor.

#### Scenario: Registro automático de evento de auditoria
- **WHEN** o status de um mantenedor for criado, aprovado ou revogado
- **THEN** a tabela `mantenedores_auditoria` MUST receber um novo registro contendo `id`, `mantenedor_id`, `croqui_id`, `usuario_id`, `acao` (`SOLICITACAO`, `APROVACAO`, `REVOGACAO`), `autor_acao_id` e `data_hora`

### Requirement: Edge Function de Resolução de Mantenedores
O backend do Supabase MUST fornecer uma Edge Function segura para consulta dos mantenedores ativos autorizados para um determinado croqui.

#### Scenario: Consulta de mantenedores autorizados por croqui
- **WHEN** a Edge Function `consultar-mantenedores` for chamada informando um `croqui_id` válido com token de serviço autorizado
- **THEN** ela MUST retornar a lista de IDs de usuários com status `ativo` para aquele croqui
- **AND** MUST omitir usuários com status `pendente` ou `revogado`
