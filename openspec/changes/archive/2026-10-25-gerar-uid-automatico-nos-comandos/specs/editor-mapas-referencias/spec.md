# Spec Delta

## MODIFIED Requirements

### Requirement: Criação de Nova Referência via Busca
The system SHALL permitir a adição de novas referências buscando entidades lógicas (Grupos, Setores, Escaladas) no CroquiModel, incluindo entidades recém-adicionadas na sessão atual ainda não salvas em disco.

#### Scenario: Busca por entidade
- **WHEN** o usuário clica em "Nova Referência"
- **THEN** um modal de busca abrangendo todo o croqui é exibido para seleção do alvo

#### Scenario: Referência imediata para entidade recém-adicionada sem salvar
- **WHEN** o usuário adiciona uma nova Escalada, Setor ou Grupo na aba de Dados e, sem salvar o croqui em disco, cria uma nova referência para essa entidade no Editor de Mapas
- **THEN** a referência é criada com `alvo_uid` preenchido com o `uid` da nova entidade e o painel de referências exibe imediatamente o caminho hierárquico formatado da entidade em vez de `"Referência Inválida"`
