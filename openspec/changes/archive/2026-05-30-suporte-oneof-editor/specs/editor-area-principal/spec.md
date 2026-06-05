## ADDED Requirements

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
