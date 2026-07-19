## Context

Os arquivos antigos do Ouroboulder (`.webp`) não passaram por um processo padronizado direto do Illustrator. Eles têm baixa resolução (`~1999x1499`), proporções às vezes erradas, e legendas pintadas na imagem.
Temos no entanto uma pasta com exportações em altíssima qualidade (`4x`, `~7681x5761`) originadas perfeitamente de pranchetas individuais no Illustrator, com duas versões: com legendas (bom para OCR) e sem legendas (melhor para usar na versão final com POIs).
O maior desafio técnico não é apenas substituir as imagens, mas lidar com as restrições arquiteturais da substituição (dimensões mudam de 1999 para 2364 via Lanczos resampling, devido ao cap de 4Megapixels do banco). 

## Goals / Non-Goals

**Goals:**
- Mapear via PaddleOCR as pranchetas com legendas e descobrir a qual Bloco/Grupo pertencem.
- Renomear automaticamente todas as imagens de pranchetas com legenda e sem legenda.
- Comprimir a versão "sem legenda" substituindo os artefatos atuais em `.webp`.
- Aplicar fator de escala matemático preciso `(nova_dimensão / antiga_dimensão)` a todos os metadados JSON e propriedades YAML dos arquivos Markdown referentes aos mapas.

**Non-Goals:**
- Recriar pontos de interesse via Agentes Visuais.
- Trocar nomes ou ids de setores e blocos já estabelecidos.

## Decisions

1. **Uso de PaddleOCR e Heurística de Arquivo**: Um script rodará e lerá `Bloco: <Nome>` e `Setor: <Nome>`. Ele também extrairá o nome base original `Prancheta X@4x`. Mapearemos os arquivos `.webp` correntes em `imagens/` que referenciam o mesmo `Bloco` e `Setor`, para encontrar qual seria o target path de destino (ex: `grupo_pedreira_setor_bloco_longevidade_p0.webp`).
2. **Compressão**: Usar nativamente o `scripts/comprimir_imagens.py` que limitará a proporção em max_area=4194304.
3. **Escala**: O fator de ajuste será calculado individualmente para cada mapa como `novo_width / antigo_width`. Propriedades de `pontos_de_interesse` que serão convertidas via um novo script utilitário: `x`, `y`, `raio`, `comprimento`, e `largura`. E o arquivo atualizará `largura_mapa` e `altura_mapa`.

## Risks / Trade-offs

- **[Risco] Mapeamento Ambíguo de Múltiplas Páginas (`p0`, `p1`)**: Ao mapearmos imagens, pode haver várias pranchetas para o mesmo bloco. 
  - **Mitigação**: O script vai procurar diretamente dentro da lista de `mapas` do arquivo `.md` do Bloco respectivo. Como o número de imagens e a ordem bate exatamente com o número de mapas cadastrados no `.md`, mapearemos sequencialmente pegando a URL exata do atributo `caminho_imagem_mapa` do Markdown! Isso acaba com qualquer risco de divergência de nome, inclusive para blocos de mapa único. Além disso, o fluxo inclui uma pausa para revisão manual do arquivo JSON antes da execução.
- **[Risco] Corrupção de Precisão no Float**: Redimensionamentos inteiros de `x` e `y` em pixels podem arredondar de forma que as marcações errem.
  - **Mitigação**: Como `7681 -> 2364` e `1999 -> 2364`, o delta da diferença de aspect ratio não muda, a imagem só fica esticada. Multiplicar em float e dar `round` pro int mais próximo (Python `int(round())`) é suficiente para o uso visual de um croqui sem erro perceptível humano.
