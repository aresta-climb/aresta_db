## Purpose

Define o mecanismo pelo qual aprovações de sugestões de croquis realizadas por mantenedores locais (autenticados no Supabase e sem conta no GitHub) são validadas e traduzidas em aprovação oficial pelo GitHub App do Aresta no repositório.

## ADDED Requirements

### Requirement: Validação de Mantenedor Autorizado para Pull Request
O sistema de integração MUST validar se o usuário que solicitou a aprovação é um mantenedor ativo do croqui modificado na Pull Request antes de emitir a aprovação no GitHub.

#### Scenario: Mantenedor válido aprova sugestão de seu croqui
- **WHEN** um mantenedor autenticado no Supabase enviar comando de aprovação para um PR que modifica apenas o seu croqui sob responsabilidade
- **THEN** a Edge Function `aprovar-sugestao-pr` MUST verificar a relação ativa na tabela `mantenedores_croquis`
- **AND** emitir uma revisão de aprovação (`pull_request_review: approved`) ou comentário `/approve` no GitHub utilizando o token do GitHub App do Aresta
- **AND** incluir no corpo da mensagem o nome completo do mantenedor que aprovou a alteração

#### Scenario: Usuário sem autorização tenta aprovar sugestão
- **WHEN** um usuário autenticado tentar aprovar um PR de um croqui do qual não é mantenedor ativo
- **THEN** a Edge Function MUST rejeitar a requisição com erro de autorização HTTP 403
- **AND** NENHUMA ação de aprovação MUST ser disparada no GitHub

### Requirement: Preservação de Permissão Global dos Devs do Aresta
O sistema MUST manter a capacidade irrestrita dos desenvolvedores do Aresta de aprovar diretamente qualquer Pull Request no GitHub.

#### Scenario: Desenvolvedor global aprova Pull Request diretamente
- **WHEN** um membro, colaborador ou proprietário do repositório (`OWNER`, `MEMBER`, `COLLABORATOR`) aprovar o PR diretamente na interface do GitHub ou via comentário `/approve`
- **THEN** o fluxo de integração MUST acatar a aprovação imediatamente, independente do cadastro de mantenedores locais daquele croqui
