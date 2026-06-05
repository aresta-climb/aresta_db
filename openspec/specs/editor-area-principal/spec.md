## Purpose
Define a estrutura e o comportamento da janela principal do editor de croquis, incluindo as barras de ferramentas e a navegação entre as visões do sistema.
## Requirements
### Requirement: Moldura Principal da Janela
A Janela Principal do editor SHALL ser dividida em três regiões distintas: uma barra de ferramentas superior (Top Toolbar), uma barra de ferramentas lateral esquerda (Side Toolbar) e uma área de conteúdo central. A área central atuará como âncora principal para os editores de dados, imagens e mapas gerenciados pelo roteamento do "Editor de Dados".

#### Scenario: Visualização inicial da Janela Principal
- **WHEN** o aplicativo é inicializado após a seleção de um croqui
- **THEN** a janela principal deve ser exibida com as três áreas visíveis e a área central exibindo inicialmente a página de "Dados", carregando a visão de árvore na lateral esquerda dessa área central.

### Requirement: Barra de Ferramentas Superior (Top Toolbar)
A Top Toolbar SHALL conter ícones premium (via QtAwesome) para ações globais e um logo de montanha no canto esquerdo.
- **Alinhamento**: SHALL possuir um espaçador inicial de 63px para alinhar o conteúdo com a área central.

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
    4. Exibir uma notificação discreta de sucesso (Toast) no canto inferior direito, sem interromper o fluxo com caixas de diálogo modais.

#### Scenario: Interação com botões Desfazer/Refazer
- **WHEN** o usuário clica em "Desfazer" ou "Refazer"
- **THEN** o sistema SHALL executar a ação correspondente no histórico de comandos do croqui

#### Scenario: Interação com botão Exportar
- **WHEN** o usuário clica no botão "Exportar" na barra superior
- **THEN** o sistema SHALL gerar o arquivo `.croqui` (ZIP) com os dados do croqui

### Requirement: Barra de Ferramentas Lateral (Side Toolbar)
A Side Toolbar SHALL conter ícones premium (via QtAwesome) dispostos verticalmente na lateral esquerda, permitindo alternar entre as visões: Dados, Imagens, Mapas e Histórico.
- **Dimensões**: SHALL possuir 82px de largura total.
- **Botões**: SHALL possuir margens de 6px em todos os lados.

#### Scenario: Seleção de visão na barra lateral
- **WHEN** o usuário clica em um dos ícones da barra lateral (Dados, Imagens, Mapas ou Histórico)
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir a visão correspondente.

#### Scenario: Seleção de visão na barra lateral (Imagens)
- **WHEN** o usuário clica no ícone de "Imagens" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de imagens integrado.

#### Scenario: Seleção de visão na barra lateral (Mapas)
- **WHEN** o usuário clica no ícone de "Mapas" na barra lateral
- **THEN** o conteúdo da área central SHALL ser atualizado para exibir o editor de mapas integrado, permitindo a edição visual dos POIs dos mapas do croqui atual.

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

### Requirement: Carregamento e Escrita de Arquivos Externos
A Área Principal SHALL ler e persistir recursivamente os arquivos externos com a extensão `.md` contidos no diretório `database/` para setores, grupos e arquivos markdown associados.
- **Carregamento**: Ao carregar o croqui, o sistema SHALL varrer as referências de arquivos externos e preencher o campo `conteudo` correspondente em memória. Propriedades estruturadas devem ser extraídas do YAML frontmatter, e a descrição textual extraída do corpo do markdown do arquivo `.md`. O sistema SHALL manter referências estáveis em memória aos objetos de conteúdo para evitar perdas ou instabilidade de referências.
- **Salvamento**: Ao salvar o croqui, o sistema SHALL realizar uma cópia profunda (deep copy) da estrutura do croqui para isolar a gravação e evitar limpar os campos `conteudo` ativos na interface gráfica. O sistema persistirá os arquivos `.md` contendo o YAML frontmatter atualizado e o corpo do markdown correspondente.
- **Renomeação e Exclusão**: Se o nome do arquivo associado for alterado na UI, o sistema SHALL atualizar a referência no arquivo `croqui.yaml`, escrever o novo arquivo físico no disco e excluir com segurança o arquivo físico antigo.

#### Scenario: Carregamento Recursivo de Arquivos Externos
- **WHEN** o croqui é carregado na Janela Principal
- **THEN** o sistema SHALL ler todos os arquivos `.md` referenciados, preenchendo as propriedades estruturadas e o markdown em memória, eliminando a exibição de wrappers vazios.

#### Scenario: Salvamento Seguro e Sincronização
- **WHEN** o usuário clica em "Salvar"
- **THEN** o sistema SHALL:
    1. Realizar cópia profunda do croqui.
    2. Escrever os arquivos externos `.md` atualizados.
    3. Excluir os arquivos antigos que foram renomeados.
    4. Atualizar o `croqui.yaml` com as novas referências.
    5. Manter os objetos de dados em memória intactos e editáveis no editor.

