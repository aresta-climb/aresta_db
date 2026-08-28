## MODIFIED Requirements

### Requirement: Interface PyQt de Curadoria
O sistema SHALL exibir os resultados da busca cruzada na interface do Editor Desktop para validação humana utilizando componentes gráficos do PySide6.

#### Scenario: Apresentação da lista de vídeos e imagens
- **WHEN** o curador abre a nova aba do editor
- **THEN** o sistema MUST carregar os candidatos de forma assíncrona.
- **THEN** o sistema MUST tentar baixar e renderizar as imagens das URLs de thumbnails como `QPixmap` nativos do PySide6. Caso a API de busca não forneça um thumbnail válido (comum no Instagram), o sistema MUST aplicar uma imagem estática de fallback.
- **THEN** a lista MUST ser ordenada pelo score de confiança do LLM e MUST dar destaque visual para resultados cruzados (ex: links que apareceram em múltiplas fontes com match do nome).
