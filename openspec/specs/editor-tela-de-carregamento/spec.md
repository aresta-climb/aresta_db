# editor-tela-de-carregamento Specification

## Purpose
Define a interface e as funcionalidades da tela de carregamento do Editor Aresta.
## Requirements
### Requirement: Layout da Tela de Carregamento
A Tela de Carregamento MUST ser a visualização de entrada da aplicação. Ela MUST ser um `QDialog` flutuante e compacto, exibido de forma centralizada na tela do usuário, dividido em uma área de ações principais no topo e uma área de histórico de croquis experimentais na base.

#### Scenario: Abertura da Aplicação
- **WHEN** a aplicação for iniciada e a tarefa de inicialização concluída
- **THEN** a aplicação MUST exibir a "Tela de Carregamento" como um diálogo independente

### Requirement: Ações de Gerenciamento de Croquis
A aplicação MUST apresentar três botões distintos: "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial". Cada botão MUST executar sua respectiva ação de gerenciamento.

#### Scenario: Novo croqui
- **WHEN** o usuário clica no botão "Novo croqui"
- **THEN** a aplicação MUST abrir um diálogo solicitando obrigatoriamente: Nome do Pico de Escalada, Cidade, Estado (UF) e País.
- **THEN** o campo "ID do Croqui" MUST ser preenchido automaticamente seguindo o padrão `<pais>_<estado>_<cidade>_<nome_do_pico_em_snake_case>` (tudo em letras minúsculas) e MUST ser somente leitura para o usuário.
- **THEN** a aplicação MUST exibir um indicador visual (ícone verde/vermelho) e uma mensagem ao lado do ID informando se ele está disponível ou se já existe.
- **THEN** o botão de confirmação MUST estar desabilitado se o ID gerado já existir no storage local.
- **THEN** ao confirmar os dados, a aplicação MUST criar o diretório do croqui no storage local.
- **THEN** a aplicação MUST gerar um arquivo `croqui.yaml` inicial seguindo a estrutura da mensagem `Croqui` do `croqui.proto`.
- **THEN** a aplicação MUST executar uma compilação inicial do croqui e salvar na pasta `compilado` do projeto.
- **THEN** a aplicação MUST atualizar a lista de histórico e abrir o croqui para edição.

#### Scenario: Importar croqui experimental
- **WHEN** o usuário clica no botão "Importar croqui experimental"
- **THEN** a aplicação MUST abrir um diálogo de seleção de arquivo filtrando por extensão `.croqui` (preferencial) ou `.zip`
- **THEN** após a seleção, se for um arquivo `.croqui`, a aplicação MUST realizar a desofuscação do magic number (XOR 0xFF no primeiro byte)
- **THEN** a aplicação MUST extrair o conteúdo, normalizar a estrutura do arquivo (remover pastas raiz extras), inicializar o Git se necessário e atualizar a lista de histórico

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

