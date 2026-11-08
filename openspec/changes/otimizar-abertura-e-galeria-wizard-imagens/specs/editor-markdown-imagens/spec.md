## MODIFIED Requirements

### Requirement: Galeria de Imagens do Croqui Atual
O diálogo SHALL listar todas as imagens disponíveis na pasta `imagens/` e na memória RAM do croqui atual com pré-visualização de miniaturas e busca rápida, carregando a galeria sob demanda ao acessar a aba `"Imagens do Croqui"` sem bloquear a abertura inicial do diálogo.
- **Carregamento Sob Demanda (*Lazy*) e Cache de Miniaturas**: A listagem e a geração de miniaturas `96x96` SHALL ocorrer apenas quando a aba `"Imagens do Croqui"` for exibida, reutilizando um cache em memória invalidado por modificação do arquivo ou dos bytes em RAM.
- **Visualização em Grade**: Cada imagem da pasta `imagens/` ou da memória RAM SHALL ser representada com sua miniatura `96x96` e nome de arquivo.
- **Filtro Textual**: O diálogo SHALL fornecer um campo de busca para filtrar dinamicamente a lista de imagens pelo nome do arquivo.

#### Scenario: Abertura da Aba Galeria Sob Demanda com Cache de Miniaturas
- **WHEN** o usuário abre o diálogo de inserção de imagem no Markdown e alterna para a aba `"Imagens do Croqui"`
- **THEN** a galeria SHALL popular os itens sob demanda reutilizando miniaturas `96x96` em cache para arquivos inalterados e atualizando qualquer imagem modificada em memória RAM

#### Scenario: Filtragem de Imagens na Galeria
- **WHEN** o usuário digita um termo no campo de busca do diálogo
- **THEN** a galeria SHALL exibir apenas as imagens cujo nome do arquivo contenha o termo digitado.
