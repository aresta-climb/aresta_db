## MODIFIED Requirements

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
