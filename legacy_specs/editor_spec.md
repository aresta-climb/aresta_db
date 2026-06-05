# Especificação Técnica e de Design - Editor de Croquis

## 1. Visão Geral
O **Editor Aresta** é uma ferramenta desktop auxiliar projetada para facilitar a criação e iteração de croquis de escalada. Ele permite que autores locais editem arquivos, visualizem o resultado instantaneamente no aplicativo móvel e submetam suas alterações para produção via Pull Request, sem a necessidade de configurar ambientes de desenvolvimento complexos.

## 2. O Formato de Arquivo `.croqui`
Para garantir uma experiência de usuário fluida e "nativa", a ferramenta utiliza uma extensão proprietária.

- **Natureza:** Um arquivo ZIP renomeado para `.croqui`.
- **Estrutura Interna:**
    - `indice.binarypb`: índice do croqui experimental, metadados do setor e hashes (SHA256) de cada arquivo para controle de integridade.
    - `compilado.binarypb`: conteúdo binário de setores, vias e acessos.
    - `imagens/`: Repositório de imagens (croquis traçados, fotos de base, etc).

## 3. Arquitetura da Ferramenta Desktop
A ferramenta é desenvolvida em Python para garantir agilidade e reaproveitamento da lógica de backend.

### Stack Tecnológica
- **GUI:** PyQt6 (Interface rica, estável e com widgets nativos).
- **Processamento:** Python 3.x com bibliotecas de manipulação de imagem e compressão.
- **Integração GitHub:** `PyGithub` para automação de commits e `requests` para o fluxo de autenticação OAuth.

### Distribuição e Empacotamento
A distribuição é automatizada via **GitHub Actions** e PyInstaller utilizando uma estratégia de *Matrix Build*:
- **Windows:** `.exe` (pyinstaller `--onefile --windowed`).
- **Linux:** Pacote `.AppImage` para garantir que as bibliotecas do Qt rodem em qualquer distribuição.
- **macOS:** Arquivo `.app` (suporte para Intel e Apple Silicon).

## 4. Integração com o Aplicativo Mobile (Flutter)
O aplicativo principal reconhece o arquivo experimental para visualização imediata.

### Abertura via Sistema Operacional
- **Android:** Implementação de `Intent Filters` no `AndroidManifest.xml` para interceptar arquivos com extensão `.croqui`.
- **iOS:** Registro de *Uniform Type Identifiers* (UTI) no `Info.plist`.

### Modo Preview Experimental
Ao abrir um arquivo `.croqui`, o app entra em estado de **Visualização Local**:
- Os dados **não são persistidos** no banco de dados local permanente.
- O app limpa o cache desse croqui assim que a sessão de visualização é fechada.
- Isso evita conflitos com versões oficiais do banco de dados de produção.

## 5. Fluxo de Trabalho do Autor (Workflow)

1. **Download:** O autor baixa o executável do aplicativo desktop da página de artefatos do projeto no Github. O aplicativo abre sem necessitar de nenhuma instalação a mais.
1. **Edição:** O autor modifica o croqui pela interface gráfica do aplicativo desktop.
2. **Compilação:** O autor clica em "Compilar" na ferramenta desktop. O script gera o manifesto e o pacote `.croqui`.
3. **Transferência (Via Dupla):**
   - **Caminho Feliz:** A ferramenta gera um QR Code. O autor escaneia com o celular e o app baixa o arquivo via rede local/Wi-Fi (HTTP Server temporário). Suporte a atualização incremental igual em produção.
   - **Fallback:** O autor transfere o arquivo `.croqui` manualmente (WhatsApp, Drive, Cabo) e clica para abrir no celular. Nesse modo de "backup", o croqui inteiro precisa ser empacotado toda vez. Permite compartilhamento de croquis em desenvolvimento.
4. **Validação:** O autor revisa o traçado e os textos diretamente no celular.
5. **Submissão:** O autor clica em "Enviar para Produção" na ferramenta desktop.
   - O app solicita autorização via **GitHub Device Flow** (sem necessidade de criar Tokens manuais).
   - A ferramenta faz o fork, commit e abre a **Pull Request** automaticamente.

## 6. Segurança e Robustez
- **GitHub OAuth:** Utilização de *Device Authorization Grant* para que leigos não precisem lidar com Personal Access Tokens (PAT).
- **Servidor Local Efêmero:** O servidor de arquivos local roda em uma porta aleatória e apenas enquanto a janela de QR Code estiver aberta, minimizando riscos de segurança.
- **Validação de Sintaxe:** O compilador valida o Markdown antes de gerar o pacote, prevenindo erros de renderização no aplicativo móvel.

## 7. Interface do Aplicativo
O design do aplicativo deve ser clean, moderno e fácil de usar. O usuário deve se sentir confortável ao editar o croqui e não deve ter dificuldade em encontrar as ferramentas que precisa.

Essa seção descreve as páginas do aplicativo.

### 7.1. Inicialização
O aplicativo deve criar uma pasta em local storage (por exemplo, %appdata% ou pasta equivalente no Linux/Mac) para armazenar os dados do aplicativo.

Nessa pasta, será feito o download do último commit do repositório de aresta_db usando o próprio git. A pasta será a base do repositório local.

### 7.2. Página inicial
O layout deve ser dividido em duas partes:

1. Botões para abrir novos croquis. Serão três botões:
  a. **Novo croqui:** Cria um novo croqui em branco. Pede inicialmente as informações necessárias para criar a pasta do croqui: país, estado, cidade e nome do pico.
  b. **Importar croqui experimental:** Abre uma janela para selecionar um arquivo .croqui para ser aberto e editado.
  c. **Editar croqui oficial:** Sincroniza o repositório aresta_db com o último commit e mostra os croquis oficiais disponíveis para serem abertos e editados. Ao selecionar um croqui, o croqui é copiado e se torna um croqui experimental para ser editado.
2. **Croquis experimentais:** Lista de croquis experimentais que foram criados até agora, com última data de edição, para ser aberto e continuar a iterar no aplicativo. Todo novo croqui importado para o aplicativo passa a aparecer aqui. Ao fazer o double click em um croqui, abre a página de edição desse croqui.

### 7.3. Criação de croquis experimentais

Croquis experimentais são salvos na pasta `croquis_experimentais` do local storage, e seguem o seguinte formato de pastas:
* `<timestamp_segundos>_<pais>_<estado>_<cidade>_<nome_do_pico>/`: pasta principal
  * `croqui_experimental.yaml`: arquivo YAML com os metadados do croqui experimental, seguindo o proto CroquiExperimental em croqui_experimental.proto.
  * `database/`: pasta que contém o croqui descompilado (mesmo formato dos croquis nas pastas `aresta_db/database/<croqui>`).
    * `croqui.yaml`: arquivo YAML principal que representa a mensagem Croqui, quebrada em vários sub-arquivos para mais fácil entendimento do croqui descompilado.
    * `*.md`: arquivos Markdown com Frontmatter YAML que representam as partes do Croqui e que são imporatdas pelo arquivo `croqui.yaml` principal.
    * `imagens/`: contém todas as imagens do Croqui.
  * `generated/`: pasta que contém o croqui compilado pronto para ser aberto para o aplicativo (mesmo formato dos croquis nas pastas `generated`).
    * `indice.binarypb`: índice do croqui experimental, metadados do setor e hashes (SHA256) de cada arquivo para controle de integridade.
    * `compilado.binarypb`: versão compilada da mensagem Croqui, com imagens relativas à pasta principal do croqui (ou seja,
         `database/imagens/...` ou `generated/imagens_geradas/...`).
    * `imagens_geradas/`: contém todas as imagens geradas pela compilação do croqui, como a thumbnail.
  * `.git`: repositório local desse croqui experimental para controle de histórico das edições do croqui experimental. Nunca vai virar um repositório no GitHub, é estritamente local.

Ao criar um croqui experimental, ele deverá ser copiado para a pasta `croquis_experimentais` do local storage, com a pasta do croqui seguindo o formato acima. Em seguida, o croqui deverá ser aberto na página principal.

## 8. Área principal
O croqui nada mais é do que uma instância da mensagem `Croqui` definida em `croqui.proto`. A página de edição irá ler o croqui da pasta `<croqui_experimental>/database/`, e irá escrever mudanças de volta para essa mesma pasta, sem mudar a estrutura.

O propósito da área principal deve ser permitir que o autor acesse todas as funcionalidades do aplicativo. A área principal é composta por três áreas principais:
1. A toolbar clássica no topo da tela com os botões de salvar, desfazer, refazer, compilar, exportar, conectar com celular, etc.
2. uma toolbar lateral esquerda para visões diferentes do aplicativo, similar aos ícones de "Explorer", "Code Search", "Source Control", etc do VS Code. Esse toolbar terá inicialmente um botão para cada página do aplicativo.
3. O resto da área do aplicativo que será preenchida com páginas selecionadas pela toolbar lateral.

Ao clicar em um desses botões da toolbar lateral, todo o conteúdo à direita dessa toolbar será preenchido por uma página que preencherá todo o resto da área disponível. Abaixo descrevemos cada uma das páginas possíveis. O conteúdo das páginas vai descrever apenas esse conteúdo interno, sem descrever novamente o toolbar lateral. Nota que cada página pode adicionar novos botões na toolbar do topo da página, que desaparecerão ao mudar de página.

### 8.1. Página de Editor

O propósito da página de editor deve ser permitir que o autor edite os campos da mensagem `Croqui`. No entanto, o croqui é uma estrutura complexa e profundamente interligada, tornando impossível editar tudo de forma eficiente somente através de um formulário. Portanto, o editor possui duas partes principais:

1. Uma "janela" ocupando toda a parte esquerda da tela, similar ao Explorer do VS Code, com uma visão de árvore da mensagem Croqui e suas sub-mensagens, com a possibilidade de abrir ou fechar partes da árvore através de um ícone à esquerda do nome da mensagem. Ao clicar na mensagem, abre-se aquela sub-mensagem na parte principal da página de edição.
2. A parte principal da página de edição, onde será possível editar os campos da sub-mensagem selecionada. Ao editar um campo, o aplicativo irá atualizar o croqui na memória, mas não irá salvar as mudanças no arquivo até que o autor clique em "Salvar" na barra de ferramentas.

A parte principal da página de edição pode ser customizada para cada mensagem da árvore protobuf sendo editada. Cada mensagem terá sua própria sub-página. Abaixo estão descritas as sub-páginas possíveis:

#### 8.1.1. Editor de dados

É uma sub-página que tem as funcionalidades "padrão" e simples para edição de qualquer mensagem protobuf. Essa sub-página renderiza uma mensagem protobuf como um formulário, onde cada campo é apresentado da forma correta para o tipo de dado:
* Para todos os tipos de campos: devem ter a descrição do campo acima extraída do comentário do campo na mensagem protobuf.
* Campos escalares: devem mostrar o conteúdo do campo escalar por padrão caso presente, mas também indicar que o campo está vazio (o que é diferente de um valor default da mensagem, como uma string vazia), com um botão de apagar o campo para retornar o campo ao estado default. As seguintes apresentações devem ser usadas para cada tipo de campo:
  * Strings: campos de texto, sempre em UTF-8. Podem ser customizados (ver "Customização de strings de texto").
  * Inteiros, floats e doubles: campos numéricos com botões de incremento e decremento
  * Booleanos: checkboxes
  * Enums: dropdown com os valores possíveis. Um "enum value option" na mensagem protobuf pode customizar qual é o texto de exibição para cada valor possível.
  * Bytes: campo de texto multiline com o conteúdo mostrado no editor encodado em base64, mas salvo em formato binário no protobuf. Podem ser customizados (ver "Customização de campos `bytes`").
* Repetições: lista de itens com botões de adicionar e remover
* Proto maps: similar a repetições, mas com chave e valor
* Mensagens aninhadas: por padrão são apenas um botão de adicionar / remover / abrir a sub-mensagem, criando um novo elemento na árvore do protobuf do painel lateral esquerdo. Nesse caso, abrir a sub-mensagem abre uma nova instância da sub-página de visualização da mensagem. Podem ser customizados (ver "Customização de mensagens aninhadas").

##### 8.1.1.1. Reusabilidade

Cada uma das implementações de visualização dos tipos de campo mencionados acima serão empacotados em uma classe especializada, para que possam ser facilmente implementados e utilizados por outras sub-páginas customizadas para cada tipo de mensagem.

##### 8.1.1.2. Customização de campos `bytes`

Caso uma field option especifique o mime type do campo bytes, por exemplo `image/jpeg`, o campo deve ser mostrado como um botão de download com o nome "<nome_do_campo>.<extensao>" em vez de um campo de texto. O botão de download deve ter um ícone de arquivo ao lado do nome do arquivo. Ao clicar no botão de download, o arquivo deve ser salvo no diretório de downloads do usuário. Deve também ter um botão para importar um arquivo binário do computador da pessoa para substituir o valor atual. Além disso, pode ser mostrada uma pré-visualização do conteúdo dependente do mime type. Por exemplo, imagens já aparecem com uma pré-visualização da imagem referida.

Note que há também o mime type especial `message/<tipo>`, que armazena uma mensagem serializada do tipo `tipo`, que no caso deve ser mostrada como uma mensagem aninhada natural, apenas com o conteúdo serializado nesse campo bytes.

##### 8.1.1.3. Customização de strings de texto

Strings de texto são por padrão mostradas como um campo single line de texto. Poré, dependendo de uma field option especificando o Mime type do conteúdo da string, pode haver uma apresentação especial:
    * Padrão: apenas uma linha, string comum.
    * `text/markdown`: deve se mostrar como um editor de múltiplas linhas markdown, com uma caixa de texto à esquerda permitindo edição do raw markdown, e uma caixa à direita mostrando a pré-visualização.
    * `link/<mime type>`: deve representar um link para um arquivo que contém o determinado tipo de acordo com o mime type. Por exemplo, `link/image/jpeg` deve representar um link para um arquivo jpeg. O campo deve ser apresentado como um campo de texto mostrando o link para o arquivo, com uma pré-visualização do conteúdo dependente do mime type, exatamente como um campo do tipo `bytes`. 
    * `link/message/<tipo>`: um tipo especial de campo de link que deve se mostrar com um campo de texto de caminho para um arquivo, com esse arquivo sendo um Markdown com Frontmatter YAML que representa uma sub-mensagem. Essa sub-mensagem deve ser renderizada no editor exatamente como uma mensagem aninhada do tipo `<tipo>`, podendo ser customizada a apresentação seguindo o message option da mensagem.

##### 8.1.1.4. Customização de mensagens aninhadas

Em mensagens aninhadas, em qualquer uma das representações abaixo, pode ser customizada a representação da mensagem aninhada:
* Sub-mensagens da mensagem atual do protobuf
* Strings de texto com o field option de mime type `link/message/<tipo>`
* Campos `bytes` com o field option de mime type `message/<tipo>`

A representação da mensagem aninhada vai depender de um message option, que controla como a mensagem é mostrada no editor. Por padrão, as mensagens são mostradas como uma nova sub-página de edição padrão, mas com o message option pode ser especificada alguma das seguintes opções:
* Visualização inline: os sub-campos da mensagem aninhada são mostrados como collapsible sections, com um botão de expandir/fechar, abrindo uma nova sub-página do editor padrão para a mensagem inline no editor atual, em vez de uma nova sub-página. 
* Páginas customizadas: pode ser especificado um tipo diferente de sub-página customizada, que vai abrir ao clicar na mensagem na visão de árvore em vez de abrir a sub-página do editor padrão. Essa sub-página pode customizar sua apresentação como quiser, e é registrada por um ID que representa a sub-página e pode ser referenciada na message option.

Essas páginas customizadas são descritas a seguir.

#### 8.1.2. Editor de imagens (`EDITOR_IMAGENS`)

O editor de imagens permitirá que o autor edite imagens que estão no croqui, com algumas funcionalidades básicas de edição. Ele deverá ter como base o script `scripts/editar_imagens.py`, tendo as mesmas funcionalidades.

#### 8.1.3. Editor de mapas (`EDITOR_MAPAS`)

O editor de mapas permitirá que o autor edite mapas que estão no croqui, com algumas funcionalidades básicas de edição, principalmente com relação ao controle dos pontos de interesse. Ele deverá ter como base o script `scripts/editar_mapas.py`, tendo as mesmas funcionalidades.

### 8.2. Página de Histórico

O propósito da página de histórico deve ser permitir que o autor acesse o histórico de edições do croqui e visualize o que foi alterado em cada versão. Essa página terá duas partes:

1. Uma "janela" ocupando toda a parte esquerda da tela, similar à sub-página de editor, listando todas as versões com um resumo de cada versão.
2. A parte principal da página de histórico, comparando o croqui atual com a versão que está sendo investigada, e um botão de restaurar versão.

A funcionalidade de histórico de edições é gerenciada por um repositório git local no .croqui, detalhado na especificação `editor_backups.md`.

### 8.3. Página de Imagens

O propósito da página de imagens deve ser permitir que o autor visualize todas as imagens referenciadas no croqui, e edite-as. A apresentação deve ser similar à página de editor, com uma árvore à esquerda e o Editor de imagens (`EDITOR_IMAGENS`) à direita. A diferença principal é que essa árvore vai mostrar *apenas* as imagens do croqui, para que seja fácil trocar entre todas as imagens do croqui e editar cada um deles.


### 8.4. Página de Mapas

O propósito da página de mapas deve ser permitir que o autor visualize todos os mapas referenciados no croqui, e edite-os. A apresentação deve ser similar à página de editor, com uma árvore à esquerda e o Editor de mapas (`EDITOR_MAPAS`) à direita. A diferença principal é que essa árvore vai mostrar *apenas* os mapas do croqui, para que seja fácil trocar entre todas os os mapas do croqui e editar cada um deles.