## MODIFIED Requirements

### Requirement: Ações de Gerenciamento de Croquis
A aplicação MUST apresentar três botões distintos: "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial". Cada botão MUST executar sua respectiva ação de gerenciamento.

#### Scenario: Novo croqui
- **WHEN** o usuário clica no botão "Novo croqui"
- **THEN** a aplicação MUST solicitar o ID do novo croqui (ex: br_mg_cidade_pico)
- **THEN** a aplicação MUST criar um novo croqui experimental no storage local e atualizar a lista de histórico

#### Scenario: Importar croqui experimental
- **WHEN** o usuário clica no botão "Importar croqui experimental"
- **THEN** a aplicação MUST abrir um diálogo de seleção de arquivo filtrando por extensões `.croqui` ou `.zip`
- **THEN** após a seleção, a aplicação MUST normalizar a estrutura do arquivo (remover pastas raiz extras)
- **THEN** a aplicação MUST importar o croqui, inicializar o Git se necessário, e atualizar a lista de histórico

#### Scenario: Feedback de Operação
- **WHEN** uma operação de longa duração (importação, cópia de oficial ou compilação) é iniciada
- **THEN** a aplicação MUST exibir um diálogo de log detalhado (`DialogoProgressoLog`)
- **THEN** o diálogo MUST ser fechado automaticamente se a operação for concluída com sucesso
- **THEN** se houver erro, a aplicação MUST manter o diálogo aberto e remover qualquer pasta parcial criada para manter o storage limpo

#### Scenario: Editar croqui oficial
- **WHEN** o usuário clica no botão "Editar croqui oficial"
- **THEN** a aplicação MUST abrir o diálogo de busca de croquis oficiais

### Requirement: Listagem de Croquis Experimentais
A aplicação MUST escanear a pasta de croquis experimentais e exibi-los ordenados pela data de última edição (mais recentes primeiro). Se a lista estiver vazia, a aplicação MUST exibir uma mensagem informativa.

#### Scenario: Visualização e Redimensionamento
- **GIVEN** que a aplicação possui muitos itens no histórico
- **THEN** a aplicação MUST permitir que a janela seja maximizada ou redimensionada
- **THEN** a lista de histórico MUST se expandir para ocupar o espaço disponível, facilitando a navegação

#### Scenario: Abrir croqui do histórico
- **WHEN** o usuário clica duas vezes em um item da lista de histórico
- **THEN** a aplicação MUST abrir a visualização de edição para o croqui selecionado
