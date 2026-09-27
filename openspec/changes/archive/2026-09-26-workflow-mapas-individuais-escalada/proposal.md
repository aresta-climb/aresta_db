# Proposta: Workflows de Agente para Mapas Individuais de Escalada

## Why

Com a introdução do suporte a mapas individuais em `Escalada` no Protobuf, no editor desktop e no aplicativo móvel, o pipeline de agentes que converte croquis em PDF para dados estruturados precisa ser atualizado. Atualmente, os subagentes (`ConversorMarkdown` e `ExtratorMapas`) tratam todas as imagens encontradas como mapas gerais de setor (`Setor.mapas`) ou as descartam no corpo do Markdown, impedindo que fotos aproximadas de saídas de boulder (*top-out*), posições de largada (*sit-start*) ou croquis verticais dedicados a vias específicas sejam associados diretamente à escalada correspondente.

Atualizar as skills e os scripts de suporte agora fecha o ciclo da funcionalidade, permitindo que a ingestão autônoma de novos croquis já popule mapas no nível correto com orçamento de imagem (1.0 MP @ Q85) aplicado de forma determinística pelo compilador.

## What Changes

- **Skill `converter_parte_croqui_para_markdown`**:
  - Introdução de heurísticas para o subagente `ConversorMarkdown` identificar imagens dedicadas a escaladas específicas vs. mapas gerais de setor.
  - Geração de sintaxe YAML Frontmatter com `mapas:` aninhado sob o item em `escaladas:`.
  - Remoção de instruções legadas sobre o campo obsoleto `caminho_imagem_croqui`.
- **Scripts de Extração de Mapas (Fase 3)**:
  - `scripts/preparar_extracao_de_mapas.py`: Varre recursivamente `escaladas[].mapas` além de `Setor.mapas`, gerando arquivos de metadados em `raw_mapas/` vinculados à escalada pai e executando o PaddleOCR na imagem.
  - `scripts/finalizar_mapas.py`: Atualiza dimensões e pontos de interesse identificados pelo OCR diretamente na estrutura `escaladas[].mapas` no Markdown correspondente.
- **Skill `mapa_extrair_pontos_de_interesse`**:
  - Orienta o subagente `ExtratorMapas` sobre a semântica de pontos de interesse em mapas de escaladas (marcações de *start*, *top*, crux, números de enfiada ou setas direcionais).
- **Processamento e Orçamento Determinístico (`preparar_submissao_lib.py`)**:
  - Ao migrar imagens de `raw_pdf_contents/imagens/` para `imagens/`, detecta se a imagem pertence a uma escalada ou a um setor/grupo.
  - Aplica automaticamente `AREA_MAXIMA_ESCALADA` (1.0 MP) com `QUALIDADE_WEBP_ESCALADA = 85` para mapas de escalada, e `AREA_MAXIMA_PADRAO` (2.5 MP) com `QUALIDADE_WEBP_PADRAO = 85` para setores/grupos, desonerando o modelo de linguagem do controle de resolução.

## Capabilities

### New Capabilities
- `workflow-extracao-mapas-escalada`: Extração, associação contextual e processamento de mapas individuais de escalada a partir de PDFs de croquis por subagentes e scripts determinísticos.

## Impact

- **Skills de Agentes (`.agents/skills/`)**: `converter_parte_croqui_para_markdown`, `mapa_extrair_pontos_de_interesse`.
- **Scripts de Pipeline (`scripts/`)**: `preparar_extracao_de_mapas.py`, `finalizar_mapas.py`, `preparar_submissao_lib.py`.
- **Compatibilidade**: Totalmente retrocompatível com setores e croquis já convertidos.
