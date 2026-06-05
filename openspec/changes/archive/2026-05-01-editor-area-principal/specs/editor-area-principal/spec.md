## ADDED Requirements

### Requirement: Moldura Principal da Janela
A Janela Principal do editor SHALL ser dividida em três regiões distintas: uma barra de ferramentas superior (Top Toolbar), uma barra de ferramentas lateral esquerda (Side Toolbar) e uma área de conteúdo central.

#### Scenario: Visualização inicial da Janela Principal
- **WHEN** o aplicativo é inicializado após a seleção de um croqui
- **THEN** a janela principal deve ser exibida com as três áreas visíveis e a área central exibindo inicialmente a página de "Dados" (mock "a implementar")

### Requirement: Barra de Ferramentas Superior (Top Toolbar)
A Top Toolbar SHALL conter ícones para ações globais, incluindo: Abrir novo croqui, Salvar, Desfazer, Refazer, Exportar, Conectar com Celular e Publicar.

#### Scenario: Interação com botão Publicar
- **WHEN** o usuário clica no botão "Publicar" na barra superior
- **THEN** o sistema SHALL:
    1. Verificar se há modificações não salvas (e solicitar salvamento se necessário)
    2. Abrir um diálogo para coletar título e descrição da contribuição
    3. Criar uma branch temporária, enviar as alterações para o fork do usuário e criar um Pull Request no GitHub

#### Scenario: Abrir novo croqui sem modificações
- **WHEN** o usuário clica em "Abrir novo croqui" E não há modificações pendentes
- **THEN** o sistema SHALL fechar a Janela Principal e retornar para a Tela de Carregamento

#### Scenario: Abrir novo croqui com modificações pendentes
- **WHEN** o usuário clica em "Abrir novo croqui" E há modificações não salvas
- **THEN** o sistema SHALL solicitar confirmação de salvamento antes de retornar para a Tela de Carregamento

#### Scenario: Interação com botão Salvar
- **WHEN** o usuário clica no botão "Salvar" na barra superior
- **THEN** o sistema SHALL:
    1. Persistir as alterações na pasta `database` do croqui experimental
    2. Gerar automaticamente os artefatos de saída na pasta `compilado`
    3. Realizar um commit no repositório git local

#### Scenario: Interação com botões Desfazer/Refazer
- **WHEN** o usuário clica em "Desfazer" ou "Refazer"
- **THEN** o sistema SHALL executar a ação correspondente no histórico de comandos do croqui

#### Scenario: Interação com botão Exportar
- **WHEN** o usuário clica no botão "Exportar" na barra superior
- **THEN** o sistema SHALL gerar o arquivo `.croqui` (ZIP) com os dados do croqui

### Requirement: Barra de Ferramentas Lateral (Side Toolbar)
A Side Toolbar SHALL conter ícones dispostos verticalmente na lateral esquerda, permitindo alternar entre as visões: Dados, Imagens, Mapas e Histórico.

#### Scenario: Seleção de visão na barra lateral
- **WHEN** o usuário clica no ícone de "Imagens" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de imagens (mock)

### Requirement: Gerenciamento de Croqui Experimental
A Área Principal SHALL carregar os dados do croqui a partir da pasta `<croqui_experimental>/database/` e manter uma instância da mensagem `Croqui` em memória durante a sessão.

#### Scenario: Carregamento automático do croqui
- **WHEN** a Área Principal é carregada
- **THEN** ela SHALL ler o estado atual do croqui da pasta de banco de dados experimental configurada

### Requirement: Contexto Dinâmico da Toolbar Superior
As páginas exibidas na área central SHALL ter a capacidade de adicionar e remover botões específicos de seu contexto na Toolbar Superior.

#### Scenario: Mudança de contexto limpa botões específicos
- **WHEN** o usuário troca de uma página que adicionou botões para uma página padrão
- **THEN** os botões específicos da página anterior SHALL ser removidos da Toolbar Superior
