## MODIFIED Requirements

### Requirement: Integração do Editor de Imagens
O sistema SHALL fornecer um editor de imagens integrado para processamento em lote (crop, rotação e máscaras), acessível de forma isolada ou embutido na área principal quando acionado via a visão de árvore de dados.

#### Scenario: Acesso Embutido na Árvore de Dados
- **WHEN** o usuário seleciona um nó correspondente a uma imagem na árvore do Editor de Dados
- **THEN** o sistema SHALL exibir o widget de edição de imagens (`WidgetEditorImagens`) na parte direita da área central focando exclusivamente na edição daquela imagem selecionada.

#### Scenario: Listagem de Imagens
- **WHEN** o editor de imagens é carregado em modo autônomo ou via barra lateral "Imagens"
- **THEN** o sistema SHALL listar todas as imagens presentes na pasta `imagens/` do croqui atual.
