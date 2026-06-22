## Why

A migração 0002 atual falha ao processar escaladas com o campo `id_no_mapa` quando ele utiliza o formato antigo para referenciar múltiplos mapas (ex: "1a/3c") ou quando a via pertence a múltiplos mapas. Além disso, ela insere referências de forma cega no primeiro mapa do setor, mesmo que o ponto não esteja plotado neste mapa, correndo o risco de corromper a integridade visual da exibição. Precisamos corrigir a migração para extrair esses dados complexos, e rotear estritamente cada referência validando contra os `pontos_de_interesse` de cada mapa.

## What Changes

- Refatoração completa da lógica de processamento de `id_no_mapa`, `id_no_mapa_meio`, e `id_no_mapa_fim` no script de migração.
- Introdução da separação por `/` para extrair grupos de referências ordenadas por mapa.
- Introdução da separação de números e letras no mesmo nível, garantindo que "2B" torne-se "2" e "B".
- Correspondência e validação cruzada entre os grupos extraídos e o array `pontos_de_interesse` de cada mapa no setor.
- Emissão de um relatório de validação no formato `ids_no_mapa_nao_encontrados.yaml` quando IDs configurados nas escaladas não corresponderem a pontos existentes nos mapas, protegendo o croqui contra perda de dados.

## Capabilities

### New Capabilities
- `migracao-validation-report`: Geração de relatório de IDs não absorvidos para orientar a correção no editor.

### Modified Capabilities
- `mapa-referencias-centralizadas`: Ajuste nas regras de parsing de ID (separação por `/` e parsing alfanumérico) e obrigatoriedade de correspondência total com os pontos de interesse mapeados no frontmatter.

## Impact

- Modificação exclusiva no script python `0002_centralizar_map_references.py` e em seus testes.
- Criação de arquivo `.yaml` adicional no diretório do croqui caso existam IDs desvinculados após a migração.
- A base de dados não sofrerá perdas de chaves órfãs ou inserções de IDs fantasmas nos mapas.
