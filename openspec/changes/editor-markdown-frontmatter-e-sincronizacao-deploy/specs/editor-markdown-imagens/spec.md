## ADDED Requirements

### Requirement: Ocultação e Preservação Transparente de Frontmatter no Editor Markdown
O editor de Markdown SHALL ocultar delimitadores e cabeçalhos YAML frontmatter durante a edição visual e textual bruta, preservando-os de forma transparente para reconstituição ao persistir no disco.
- **Isolamento na Edição Raw**: O campo de texto bruto do editor (`EditorTextoMarkdown`) SHALL conter apenas o corpo textual do Markdown, sem as linhas de cabeçalho `---` e comentários de licença ou metadados YAML.
- **Renderização da Pré-visualização**: O componente de preview (`AutoScalingTextBrowser`) SHALL renderizar diretamente o conteúdo Markdown limpo, sem necessidade de filtros manuais em tempo de exibição.
- **Preservação de Metadados**: O modelo SHALL manter os dados e comentários de frontmatter originais preservados em metadados de rascunho enquanto o documento estiver em memória.
- **Recomposição ao Salvar**: Ao serializar e gravar o arquivo Markdown no disco, o sistema SHALL recompor o cabeçalho frontmatter preservado no topo do arquivo caso ele existisse originalmente.

#### Scenario: Edição de arquivo Markdown com frontmatter existente
- **WHEN** um arquivo Markdown contendo cabeçalho frontmatter (ex: delimitadores `---` com comentários SPDX) é aberto no editor
- **THEN** o editor bruto exibe apenas o texto Markdown abaixo do frontmatter e a pré-visualização renderiza o mesmo texto limpo.

#### Scenario: Salvamento preservando frontmatter original
- **WHEN** o usuário edita o corpo do Markdown e executa a operação de salvamento
- **THEN** o arquivo gravado no disco contém o cabeçalho frontmatter original intacto no topo, seguido pelo novo corpo Markdown editado.

#### Scenario: Edição e salvamento de Markdown sem frontmatter
- **WHEN** um arquivo Markdown que não possui delimitadores `---` é aberto e salvo
- **THEN** o arquivo é exibido e salvo sem adicionar blocos vazios de frontmatter.
