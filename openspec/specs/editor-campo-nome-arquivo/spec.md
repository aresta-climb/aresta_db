# editor-campo-nome-arquivo Specification

## Purpose
Define o formato declarativo `CampoFormatoUi.NOME_ARQUIVO`, o componente visual de exibição somente-leitura com botão de modificação, o diálogo modal de renomeação e as regras de validação e normalização de nomes de arquivos Markdown (`.md`) no Editor Aresta.

## Requirements

### Requirement: Formato de UI para Nome de Arquivo no Protobuf
O schema Protobuf DEVE (SHALL) disponibilizar o valor `NOME_ARQUIVO` no enum `CampoFormatoUi` e aplicá-lo ao campo `MetadadosArquivoNoEditor.caminho_novo`, marcando os demais campos internos de `MetadadosArquivoNoEditor` (`caminho_original` e `dados_json_originais`) como `INVISIVEL`.

#### Scenario: Instanciação de widget pela fábrica Protobuf
- **WHEN** a fábrica de widgets do formulário é invocada para um descritor de campo anotado com `CampoFormatoUi.NOME_ARQUIVO`
- **THEN** o sistema DEVE retornar uma instância do componente especializado de nome de arquivo em vez de um campo de texto editável comum.

### Requirement: Componente de Nome de Arquivo Somente-Leitura com Ação de Modificação
O componente visual de nome de arquivo DEVE (SHALL) exibir o nome do arquivo atual em um controle de texto somente-leitura (`readOnly=True`) acompanhado de um botão `"Modificar..."`, impedindo a digitação direta inline no formulário de dados.

#### Scenario: Exibição de nome de arquivo no formulário
- **WHEN** o usuário seleciona na árvore uma entidade associada a um arquivo externo (`Setor`, `Grupo`, `ArquivoMarkdown` ou `ArquivoMapas`)
- **THEN** o formulário DEVE exibir o nome atual do arquivo em modo somente-leitura e disponibilizar o botão `"Modificar..."` ao lado.

#### Scenario: Proteção contra edição direta acidental ou automatizada
- **WHEN** o usuário ou o Robô Caótico interage diretamente com os campos de linha do formulário sem abrir o modal de modificação
- **THEN** o controle de texto do nome do arquivo NÃO DEVE permitir edição direta nem disparar mutações no modelo.

### Requirement: Validação e Normalização de Nomes de Arquivo Markdown
O sistema DEVE (SHALL) validar e normalizar nomes de arquivos `.md` de entidades externas garantindo que:
1. Espaços em branco digitados pelo usuário sejam convertidos em sublinhados (`_`).
2. O sufixo `.md` seja garantido na avaliação e no resultado final.
3. O nome completo (incluindo `.md`) tenha comprimento maior que `3` e menor ou igual a `100` caracteres (`<= 100`).
4. O tronco do nome (sem a extensão `.md`) case estritamente com a expressão regular `^[a-z0-9]+(_[a-z0-9]+)*$` (apenas letras ASCII minúsculas sem acento, dígitos e sublinhados simples entre partes, sem caracteres especiais de sistema de arquivos como `:`, `/`, `\`, `<`, `>`, `"`, `'`, `*`, `?`, `|`).
5. O nome não colida (de forma case-insensitive) com outro arquivo `.md` já existente no mesmo croqui.

#### Scenario: Normalização de espaços em sublinhados
- **WHEN** o usuário digita `"setor parede norte"` como nome de arquivo
- **THEN** o sistema DEVE normalizar a entrada para `"setor_parede_norte.md"` e considerá-la válida.

#### Scenario: Recusa de nome vazio ou apenas com extensão
- **WHEN** o nome de arquivo informado for vazio (`""`), composto apenas por espaços ou apenas por `".md"`
- **THEN** a validação DEVE rejeitar o nome informando que o nome do arquivo não pode ficar vazio.

#### Scenario: Recusa de caracteres inválidos ou separadores de diretório
- **WHEN** o nome de arquivo contiver caracteres fora de `[a-z0-9_]` no tronco (como `"YAML: 'aspas' \"duplas\""`, `"<script>alert('caos')</script>"`, acentos ou barras `/`, `\`)
- **THEN** a validação DEVE rejeitar o nome informando que apenas letras minúsculas sem acento, números e `_` são permitidos.

#### Scenario: Recusa por limite de 100 caracteres
- **WHEN** o nome de arquivo completo (incluindo `.md`) possuir mais de `100` caracteres
- **THEN** a validação DEVE rejeitar o nome informando o limite máximo de `100` caracteres.

#### Scenario: Recusa por duplicidade no croqui
- **WHEN** o nome de arquivo informado já estiver em uso por outro setor, grupo, mapa geral ou seção textual do croqui
- **THEN** a validação DEVE rejeitar o nome informando que já existe um arquivo com esse nome no croqui.

### Requirement: Diálogo Modal de Renomeação e Criação com Recusa de Nomes Inválidos
Ao clicar no botão `"Modificar..."` do componente de nome de arquivo, o sistema DEVE (SHALL) abrir um diálogo modal de renomeação que valida o texto em tempo real, exibe o motivo de invalidez e mantém o botão de confirmação desabilitado enquanto o nome for inválido, vazio ou duplicado. A mesma validação DEVE ser aplicada ao campo de nome de arquivo nos diálogos de criação de botão (`DialogoCriarBotao`) e de setor/grupo (`DialogoCriarSetorOuGrupo`).

#### Scenario: Tentativa de confirmar nome inválido no modal de renomeação
- **WHEN** o usuário abre o modal `"Modificar..."` e digita um nome vazio, com símbolos inválidos ou acima de `100` caracteres
- **THEN** o modal DEVE exibir um aviso explicativo e manter o botão de confirmação desabilitado, impedindo a alteração.

#### Scenario: Confirmação de renomeação válida com suporte a Undo e Redo
- **WHEN** o usuário digita um nome válido e único no modal `"Modificar..."` e confirma a operação
- **THEN** o sistema DEVE registrar a alteração em `ext_metadados_arquivo.caminho_novo` através da pilha global de histórico (`QUndoStack`), atualizar o texto exibido no componente somente-leitura e permitir reverter/refazer via Undo/Redo.

#### Scenario: Bloqueio do botão Criar em diálogos de criação quando o arquivo é inválido
- **WHEN** nos diálogos de criação de Botão ou de Setor/Grupo o campo de nome do arquivo `.md` estiver vazio, contiver caracteres inválidos ou exceder `100` caracteres
- **THEN** o diálogo DEVE exibir o aviso de validação correspondente e manter o botão `"Criar"` desabilitado.
