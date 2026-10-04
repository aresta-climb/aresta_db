# extracao-capas-markdown Specification

## Purpose

Permite identificar, extrair e promover imagens de apresentação embutidas no corpo de textos Markdown para o campo estruturado de foto de capa (`caminho_imagem_capa`) no YAML Frontmatter de setores e grupos.

## Requirements

### Requirement: Detecção e Extração de Capa do Markdown
O sistema SHALL prover uma rotina autônoma capaz de analisar arquivos Markdown de setores e grupos, identificar a imagem mais representativa ou a primeira imagem presente no corpo do texto, promovê-la ao campo `caminho_imagem_capa` do Frontmatter YAML e remover sua tag original `![alt](caminho)` do corpo Markdown.

#### Scenario: Extração de imagem de abertura do Markdown
- **WHEN** um arquivo de setor ou grupo contém uma imagem em Markdown logo no início de seu conteúdo textual (ex: `![Foto do Setor](imagens/setor.webp)`)
- **THEN** o sistema define `caminho_imagem_capa: imagens/setor.webp` no frontmatter YAML e remove a tag `![Foto do Setor](imagens/setor.webp)` do corpo Markdown, preservando os demais textos

#### Scenario: Preservação de arquivo quando nenhuma imagem é detectada
- **WHEN** o corpo Markdown de um setor ou grupo não possui nenhuma tag de imagem
- **THEN** o sistema mantém o arquivo Markdown e seu Frontmatter inalterados, sem adicionar o campo `caminho_imagem_capa`

### Requirement: Otimização de Resolução para 1 Megapixel
O sistema SHALL garantir que toda imagem promovida a foto de capa pelo processo de extração seja inspecionada e, caso exceda a área máxima de 1.000.000 pixels (1 MP), seja reprocessada e comprimida em WebP no padrão de qualidade 85.

#### Scenario: Imagem de capa que excede 1 Megapixel
- **WHEN** a imagem identificada como capa possui resolução superior a 1.000.000 de pixels (ex: 2048x1536 px)
- **THEN** o sistema redimensiona a imagem para no máximo 1 MP mantendo o aspecto original e sobrescreve o arquivo com a versão WebP otimizada

#### Scenario: Imagem de capa dentro do limite
- **WHEN** a imagem identificada como capa já possui resolução menor ou igual a 1.000.000 de pixels
- **THEN** o arquivo de imagem é mantido sem perdas ou re-compressões desnecessárias
