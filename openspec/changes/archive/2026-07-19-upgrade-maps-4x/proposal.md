## Why

Atualmente, os mapas do Ouroboulder estão em baixa resolução e contém as legendas originais diretamente renderizadas (hardcoded) nas imagens, poluindo a visualização. Encontramos o projeto Illustrator original, e exportamos os croquis em resolução altíssima (4x) separando as pranchetas *com* legenda e *sem* legenda, possibilitando assim substituir todas as imagens no banco de dados por versões impecáveis (sem legenda) redimensionadas pelo nosso script de compressão nativo.

## What Changes

- Extração de metadados OCR da base de imagens `original_com_legenda/4x`.
- Geração de mapeamento dinâmico (nome das pranchetas -> caminhos estruturados da API).
- Renomeação em lote de imagens originais para compatibilidade com nosso script WebP.
- Compressão e padronização (via `comprimir_imagens.py`) de todos os mapas em HD limpos na pasta oficial.
- **BREAKING**: Reescalonamento (rescale) algorítmico e matemático de todos os POIs e *bounding boxes* em todos os arquivos `.md` e `raw_mapas/*.json`, proporcionalmente ao fator de aumento da imagem comprimida final versus as antigas.

## Capabilities

### New Capabilities
- `rescale-poi-metadata`: Capacidade técnica de alterar e escalar dinamicamente e proporcionalmente o tamanho, raio e posição de POIs em croquis existentes com base no resize de sua imagem pai.

### Modified Capabilities

## Impact

Afetará o script `comprimir_imagens.py` e fará um overwrite global nos arquivos `.webp` do `database/br_mg_ouro_preto_ouroboulder/imagens`. Todos os arquivos Markdown de setor/grupo `.md` do Ouroboulder e todos os JSONs em `raw_mapas` também serão atualizados in-place para que as dimensões não se percam.
