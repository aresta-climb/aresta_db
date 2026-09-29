# extracao-imagens-pdf Specification

## Purpose

Define o comportamento de detecção determinística de fatiamento de imagens em PDFs de croquis de escalada e a extração automática de páginas íntegras renderizadas em alta resolução.

## Requirements

### Requirement: Detecção de Mosaico de Imagens Fatiadas
O sistema MUST analisar as caixas delimitadoras (*bounding boxes*) das imagens de cada página do PDF para detectar se a página contém fatias retangulares adjacentes que compõem um mosaico de imagem.

#### Scenario: Detecção de fatias adjacentes em página com transparências
- **WHEN** uma página de PDF possuir imagens cujas bordas adjacentes se tocam compartilhando limites horizontais ou verticais formando uma malha de fatiamento
- **THEN** o sistema classifica a página como fatiada e emite mensagem de identificação automática no console

#### Scenario: Página normal com fotos isoladas
- **WHEN** uma página de PDF possuir imagens isoladas que não formam mosaico adjacente (ex.: fotos separadas e logos de patrocinadores)
- **THEN** o sistema NÃO classifica a página como fatiada

### Requirement: Extração Automática de Página Completa
O sistema MUST acionar automaticamente a renderização e extração da imagem de página completa (`pX.webp`) para qualquer página em que o fatiamento for detectado, dispensando a passagem explícita da flag `--incluir-paginas`.

#### Scenario: Execução padrão em PDF com páginas fatiadas
- **WHEN** o processo de particionamento for invocado sem a flag `--incluir-paginas` em um documento contendo páginas fatiadas
- **THEN** o sistema extrai automaticamente o arquivo `pX.webp` renderizado para as respectivas páginas

#### Scenario: Execução em documento tradicional sem fatiamento
- **WHEN** o processo de particionamento for invocado sem a flag `--incluir-paginas` em um documento sem páginas fatiadas
- **THEN** o sistema preserva o comportamento tradicional, extraindo apenas os recortes individuais limpos sem gerar páginas completas adicionais desnecessárias

#### Scenario: Forçamento manual via flag CLI
- **WHEN** o usuário fornecer explicitamente a flag `--incluir-paginas`
- **THEN** o sistema extrai `pX.webp` para todas as páginas da parte independentemente do resultado da detecção automática
