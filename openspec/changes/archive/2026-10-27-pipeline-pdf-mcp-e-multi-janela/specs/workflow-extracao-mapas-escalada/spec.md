# Spec Delta: workflow-extracao-mapas-escalada

## MODIFIED Requirements

### Requirement: Detecção e Associação de Mapas de Escalada em Markdown
O subagente ConversorMarkdown MUST identificar imagens de croquis focadas exclusivamente em uma única linha de escalada e associá-las diretamente no campo `mapas` da respectiva escalada dentro da chamada atômica `aresta_alterar_campo` do setor.

#### Scenario: Conversão de imagem dedicada a boulder individual
- **WHEN** o subagente processa uma página de croqui contendo uma imagem que foca exclusivamente em um único bloco ou saída de boulder
- **THEN** o subagente inclui a imagem sob `escaladas[].mapas` no payload enviado para `aresta_alterar_campo`, preservando mapas panorâmicos com múltiplas rotas no nível do setor

#### Scenario: Remoção de campo de croqui legado
- **WHEN** o subagente processa vias com múltiplas enfiadas
- **THEN** o subagente utiliza a lista padrão `mapas` da escalada e NÃO utiliza o campo legado `caminho_imagem_croqui`

### Requirement: Preparação e Execução de OCR em Mapas de Escalada
O servidor MCP MUST substituir o uso de `PaddleOCR` e de `preparar_extracao_de_mapas.py` pela ferramenta `aresta_renderizar_mapa`, que fornece metadados vetoriais extraídos via `PyMuPDF`, imagem do mapa com grade métrica (`100px`) e réguas graduadas, além de recortes ampliados (`crops`) com mira relativa para cada ponto de interesse tanto em mapas de setor quanto em mapas de escaladas (`escaladas[].mapas`).

#### Scenario: Extração de mapas de escaladas para pasta de trabalho
- **WHEN** o subagente `ExtratorMapas` invoca `aresta_renderizar_mapa` para um mapa contido em um setor ou em `escaladas[].mapas`
- **THEN** a ferramenta retorna os candidatos de texto/desenho vetoriais do PDF (se houver), a imagem completa com grade e réguas e os recortes individuais de cada POI em uma lista intercalada `[Texto, Imagem]`

### Requirement: Finalização e Injeção de Pontos em Mapas de Escalada
O subagente `ExtratorMapas` MUST atualizar `pontos_de_interesse` diretamente no objeto `Mapa` (seja de setor ou de escalada) em memória através de `aresta_alterar_campo`, eliminando a necessidade do script `finalizar_mapas.py` e de arquivos JSON intermediários em `raw_mapas/`.

#### Scenario: Aplicação de pontos de interesse na escalada
- **WHEN** o subagente `ExtratorMapas` conclui a extração e o ajuste fino dos pontos de interesse de um mapa usando os recortes de `aresta_renderizar_mapa`
- **THEN** o subagente atualiza a lista `pontos_de_interesse` diretamente via `aresta_alterar_campo` no `Mapa` correspondente e o orquestrador persiste o croqui com `aresta_compilar` e `aresta_salvar`
