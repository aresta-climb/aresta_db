# curation-panel Specification

## Purpose
TBD - created by archiving change coleta-de-betas. Update Purpose after archive.
## Requirements
### Requirement: Interface PySide6 de Curadoria
O sistema SHALL exibir os resultados da busca cruzada na interface do Editor Desktop para validação humana utilizando componentes gráficos do PySide6.

#### Scenario: Apresentação da lista de vídeos e imagens
- **WHEN** o curador abre a nova aba do editor
- **THEN** o sistema MUST carregar os candidatos de forma assíncrona.
- **THEN** o sistema MUST tentar baixar e renderizar as imagens das URLs de thumbnails como `QPixmap` nativos do PySide6. Caso a API de busca não forneça um thumbnail válido (comum no Instagram), o sistema MUST aplicar uma imagem estática de fallback.
- **THEN** a lista MUST ser ordenada pelo score de confiança do LLM e MUST dar destaque visual para resultados cruzados (ex: links que apareceram em múltiplas fontes com match do nome).

### Requirement: Persistência In-Place
O sistema SHALL persistir a escolha da curadoria humana na fonte de verdade original.

#### Scenario: Salvamento de vídeos aprovados
- **WHEN** o usuário dá "Save" após aprovar mídias na UI
- **THEN** o sistema MUST localizar e editar diretamente os arquivos Markdown (ou YAML) da respectiva via em `grupo_*.md`, sem corromper a estrutura textual já existente no arquivo.

