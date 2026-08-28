# editor-fila-aprovacao Specification

## Purpose
Define a gestão da fila de aprovação de croquis para mantenedores, os badges visuais de status dos croquis locais, filtros de visualização e a sincronização em segundo plano na tela de carregamento.

## Requirements

### Requirement: Badges Visuais de Status nos Cards de Croquis
Cada card de croqui listado na `TelaDeCarregamento` MUST exibir um badge visual indicando seu status de colaboração atual.

#### Scenario: Identificação dos status de croquis
- **WHEN** a lista de croquis locais é exibida
- **THEN** croquis sem PR vinculada MUST exibir a tag `⚪ Não Enviado`
- **THEN** croquis com PR aberta no GitHub MUST exibir a tag `🟡 Em Revisão`
- **THEN** croquis com PR aprovada/mesclada no GitHub MUST exibir a tag `🟢 Aprovado`
- **THEN** croquis com comentários não lidos MUST exibir o indicador numérico `💬 (N)`

### Requirement: Filtros Rápidos de Status
A `TelaDeCarregamento` MUST disponibilizar botões ou chips de filtro rápido no topo da listagem de croquis em edição.

#### Scenario: Filtragem por status
- **WHEN** o usuário seleciona um filtro de status específico (ex: `Em Revisão`)
- **THEN** a listagem de croquis MUST ser filtrada instantaneamente exibindo apenas os itens correspondentes ao status selecionado
- **THEN** o botão do filtro selecionado MUST ser destacado visualmente com a contagem de itens

### Requirement: Aba de Fila de Aprovação para Mantenedores
A `TelaDeCarregamento` MUST disponibilizar uma seção/aba "Para Revisar" para usuários identificados como mantenedores de croquis.

#### Scenario: Listagem de sugestões pendentes
- **GIVEN** que o usuário autenticado possui perfil de mantenedor
- **WHEN** o usuário clica na aba "Para Revisar"
- **THEN** a aplicação MUST listar as Pull Requests abertas que solicitam alterações nos croquis sob responsabilidade do usuário
- **THEN** cada item da lista MUST exibir nome do croqui, autor da sugestão, tempo decorrido, número de comentários e botões de ação ("Inspecionar no Editor" e "Abrir no GitHub")

### Requirement: Sincronização Assíncrona e Atualização Manual
A aplicação MUST sincronizar o estado das submissões e filas de revisão de forma não-bloqueante na inicialização e permitir atualização manual sob demanda.

#### Scenario: Sincronização em segundo plano na inicialização
- **WHEN** a aplicação é aberta
- **THEN** a `TarefaInicializacao` MUST consultar os status remotos em segundo plano sem impedir o usuário de interagir com a interface
- **THEN** os badges de status MUST ser atualizados assim que a resposta remota for recebida

#### Scenario: Atualização manual via botão sincronizar
- **WHEN** o usuário clica no botão "Sincronizar" no cabeçalho da `TelaDeCarregamento`
- **THEN** a aplicação MUST disparar a consulta aos serviços remotos e atualizar os status e badges de todos os cards
