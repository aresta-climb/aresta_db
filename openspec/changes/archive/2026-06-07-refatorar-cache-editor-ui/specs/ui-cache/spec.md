## ADDED Requirements

### Requirement: Reatividade Fina na Edição e Histórico
O sistema SHALL atualizar visualmente apenas o item mutado na árvore visual ao invés de destruir e recriar toda a interface de edição a cada clique ou caractere.

#### Scenario: Digitação no editor
- **WHEN** o usuário edita o campo nome do formulário
- **THEN** o nó correspondente na árvore atualiza seu texto imediatamente, sem que outros nós se contraiam ou a interface pisque.

### Requirement: Cache de Navegação
O sistema SHALL armazenar as instâncias dos formulários gerados pelo clique nos nós e reutilizá-las em acessos subsequentes.

#### Scenario: Ida e volta de seleção
- **WHEN** o usuário clica num nó A, depois num nó B, e então volta ao nó A
- **THEN** a instância visual exata do nó A deve ser mostrada, com a mesma posição de rolagem original preservada.
