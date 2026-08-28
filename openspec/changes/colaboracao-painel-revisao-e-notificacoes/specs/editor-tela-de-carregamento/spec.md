# editor-tela-de-carregamento Delta Specification

## ADDED Requirements

### Requirement: Indicadores e Controles de Sincronização na Tela de Carregamento
A `TelaDeCarregamento` MUST exibir um botão "Sincronizar" no cabeçalho e integrar badges de status de colaboração nos cards da lista de croquis.

#### Scenario: Visualização do botão sincronizar
- **WHEN** a `TelaDeCarregamento` é renderizada
- **THEN** o cabeçalho da janela MUST conter um botão de ação com ícone de sincronização e o texto "Sincronizar"
- **THEN** clicar no botão MUST re-sincronizar os status com o backend e atualizar os cards

#### Scenario: Exibição de badges de colaboração nos cards
- **WHEN** os croquis locais são listados na `TelaDeCarregamento`
- **THEN** cada card MUST exibir o badge de status (`Não Enviado`, `Em Revisão`, `Aprovado`) e contador de comentários não lidos quando aplicável

### Requirement: Barra de Filtros de Visualização de Croquis
A `TelaDeCarregamento` MUST disponibilizar uma barra de filtros rápidos por status acima da listagem de croquis em edição.

#### Scenario: Filtragem rápida por status
- **WHEN** o usuário clica em um dos botões de filtro (`Todos`, `Não Enviado`, `Em Revisão`, `Aprovado`)
- **THEN** a lista de croquis MUST filtrar os itens exibidos em tempo real de acordo com a seleção
