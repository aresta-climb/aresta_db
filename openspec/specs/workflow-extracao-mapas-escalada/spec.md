# workflow-extracao-mapas-escalada Specification

## Purpose

Permite que os subagentes autônomos e scripts de compilação extraiam, estruturem e processem mapas individuais pertencentes diretamente a escaladas a partir de PDFs de croquis.

## Requirements

### Requirement: Detecção e Associação de Mapas de Escalada em Markdown
O subagente ConversorMarkdown DEVE identificar imagens de croquis focadas exclusivamente em uma única linha de escalada e associá-las diretamente no campo `mapas` da respectiva escalada no YAML Frontmatter.

#### Scenario: Conversão de imagem dedicada a boulder individual
- **WHEN** o subagente processa uma página de croqui contendo uma imagem que foca exclusivamente em um único bloco ou saída de boulder
- **THEN** o subagente gera o YAML Frontmatter adicionando a imagem sob `escaladas[].mapas` com o caminho em `raw_pdf_contents/imagens/`, preservando mapas panorâmicos com múltiplas rotas no nível do setor

#### Scenario: Remoção de campo de croqui legado
- **WHEN** o subagente processa vias com múltiplas enfiadas
- **THEN** o subagente utiliza a lista padrão `mapas` da escalada e NÃO utiliza o campo legado `caminho_imagem_croqui`

### Requirement: Preparação e Execução de OCR em Mapas de Escalada
O script de preparação de mapas DEVE extrair metadados e disparar o reconhecimento óptico de caracteres (OCR) para imagens contidas em `escaladas[].mapas`.

#### Scenario: Extração de mapas de escaladas para pasta de trabalho
- **WHEN** o script `preparar_extracao_de_mapas.py` analisa arquivos Markdown de setores
- **THEN** o script identifica mapas dentro de cada escalada, gera arquivos de metadados correspondentes em `raw_mapas/` com a indicação da escalada proprietária e executa o motor PaddleOCR para extrair caixas de texto

### Requirement: Finalização e Injeção de Pontos em Mapas de Escalada
O script de finalização de mapas DEVE sincronizar as dimensões reais e pontos de interesse identificados de volta para a respectiva escalada no arquivo Markdown.

#### Scenario: Aplicação de pontos de interesse na escalada
- **WHEN** o script `finalizar_mapas.py` processa arquivos JSON de mapas de escaladas
- **THEN** o script localiza a escalada correspondente no Markdown e injeta `largura_mapa`, `altura_mapa` e a lista `pontos_de_interesse` sob `escalada.mapas`

### Requirement: Orçamento e Compressão Determinística por Entidade
O script `preparar_submissao_lib.py` DEVE aplicar perfis de compressão diferenciados baseando-se no contexto de vinculação da imagem.

#### Scenario: Compressão de mapa de escalada em 1.0 MP e qualidade 85
- **WHEN** o script migra imagens referenciadas em `escaladas[].mapas` a partir de `raw_pdf_contents/`
- **THEN** o script redimensiona a imagem para no máximo 1.000.000 de pixels mantendo o aspect ratio e a comprime em formato WebP com qualidade 85

#### Scenario: Compressão de mapa de setor em 2.5 MP e qualidade 85
- **WHEN** o script migra imagens referenciadas em `Setor.mapas` a partir de `raw_pdf_contents/`
- **THEN** o script redimensiona a imagem para no máximo 2.500.000 de pixels e a comprime em formato WebP com qualidade 85
