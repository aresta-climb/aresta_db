## MODIFIED Requirements

### Requirement: Diálogo de Busca de Croquis Oficiais
A aplicação MUST fornecer um diálogo para que o usuário possa buscar e selecionar um croqui oficial do repositório para edição, pré-selecionando automaticamente o primeiro item visível da lista e iniciando a importação sem solicitar resumo de edição.

#### Scenario: Interface de Busca
- **WHEN** o diálogo de busca for aberto com croquis disponíveis na pasta `database` do repositório sincronizado
- **THEN** ele MUST apresentar um campo de texto para busca filtrável, listar todos os croquis ordenados por ID e pré-selecionar automaticamente o primeiro item da lista com o botão de confirmação habilitado

#### Scenario: Filtragem de Croquis
- **WHEN** o usuário digitar no campo de busca e pelo menos um croqui corresponder ao texto digitado
- **THEN** a lista MUST ser atualizada em tempo real para exibir apenas os croquis cujos nomes ou IDs correspondam ao texto digitado e MUST selecionar automaticamente o primeiro item visível, permitindo confirmar diretamente ao pressionar `Enter`

#### Scenario: Filtragem sem Resultados Visíveis
- **WHEN** o usuário digitar no campo de busca um termo que não corresponda a nenhum croqui
- **THEN** a lista MUST ocultar todos os itens, limpar a seleção atual, desabilitar o botão de confirmação e impedir que pressionar `Enter` selecione um item oculto

#### Scenario: Seleção e Criação de Experimental
- **WHEN** o usuário selecionar ou manter pré-selecionado um croqui da lista e confirmar (via clique em `Confirmar`, duplo clique ou tecla `Enter`)
- **THEN** a aplicação MUST iniciar imediatamente a importação exibindo o diálogo de progresso, sem exibir nenhum prompt intermediário solicitando resumo do que pretende editar
- **THEN** a aplicação MUST criar um novo croqui experimental utilizando o ID do croqui oficial selecionado
- **THEN** a aplicação MUST copiar os arquivos base (croqui.yaml, markdown, imagens) do diretório oficial para o novo diretório experimental e compilá-lo localmente
- **THEN** a aplicação MUST fechar o diálogo de busca e abrir o croqui importado
