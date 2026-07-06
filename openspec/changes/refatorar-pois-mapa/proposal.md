## Why

A extração automatizada de Pontos de Interesse (POIs) em croquis de escalada apresenta inconsistências visuais quando o agente utiliza retângulos (`box`) para delimitar áreas que poderiam ser representadas por formatos mais precisos e de proporção uniforme. A introdução explícita de `quadrado` força o agente a usar um formato 1:1, resultando em detecções mais consistentes e esteticamente mais agradáveis no mapa, além de padronizar o tamanho de POIs de escalada.

## What Changes

- **BREAKING**: O campo `box` será renomeado para `retangulo` no schema de mapas (`croqui.proto`), afetando a representação em JSON. A mensagem `BoundingBox` passará a se chamar `BoundingRetangulo`.
- Inclusão do tipo `quadrado` (`BoundingQuadrado` com lado fixo) nas opções de bounding area de pontos de interesse.
- Atualização da skill do agente (`mapa_extrair_pontos_de_interesse`) para priorizar quadrados acima de retângulos e uniformizar o tamanho relativo dos marcadores de referências de escaladas.
- Script de migração para atualizar retroativamente os metadados JSON dos croquis já processados, convertendo os campos `"box"` antigos para `"retangulo"`.
- **Governança Strict**: Toda e qualquer alteração de código gerada nesta refatoração seguirá a metodologia TDD (Test-Driven Development) rigorosa, garantindo 100% de cobertura de código (unit test coverage) antes da finalização, alinhado à documentação inegociável contida em `PRINCIPIOS.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `protobuf-migrations`: Adição de um passo de migração explícito em script para atualizar chaves textuais de `"box"` para `"retangulo"` em instâncias JSON dos croquis no disco.
- `editor-dados-arvore`: Ajuste na visualização da árvore de dados do editor para refletir os novos nomes de protobuf e permitir a exibição da `message BoundingQuadrado`.

## Impact

- `croqui.proto`: Alteração estrutural em `PontoDeInteresse.tipo_area`.
- **Backend/Scripts (Python)**: Todos os scripts (`deploy_generated.py`, `mapas_controller.py`, utilitários de visualização de PDF) precisarão ser atualizados de `.box` para `.retangulo`.
- **Skills de Agentes**: `mapa_extrair_pontos_de_interesse/SKILL.md` receberá novas instruções de priorização e homogeneidade.
- **Dados Estáticos JSON**: Os arquivos em `raw_mapas/` serão alterados (migração batch).
