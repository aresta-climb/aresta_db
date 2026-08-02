## Context

A representação atual de um "retângulo" na árvore do croqui utiliza o nome de campo `.box`, que no protobuf resulta na chave JSON `"box"`. Esse nome não é idiomático no projeto e causa confusão sobre os graus de liberdade permitidos para um LLM. A adição da estrutura explícita de "quadrado" permite restringir o grau de liberdade na hora do LLM mapear POIs com formato de símbolo (proporção 1:1), algo antes simulado via heurística incerta do prompt.
Os POIs extraídos pelo agente muitas vezes oscilam entre dimensões diferentes, quebrando a padronização visual.

## Goals / Non-Goals

**Goals:**
- Adicionar o suporte a quadrados nas bounding areas, forçando dimensões 1:1, para que os agentes de LLM gerem dados mais consistentes.
- Renomear o campo herdado e sub-ótimo `.box` para `.retangulo`.
- Fornecer script de migração que atualize retroativamente as marcações `.box` existentes no banco JSON puro.
- Treinar a skill do agente para que padronize e englobe os pontos de interesse de escalada num tamanho visualmente similar.

**Non-Goals:**
- Implementar o suporte visual da conversão no Front-End/Flutter (O usuário explicitou que fará essa etapa nativamente).

## Decisions

- **Criação de BoundingQuadrado**: A nova message `BoundingQuadrado` conterá `x`, `y` e apenas um `lado` em vez de dois graus de liberdade, impossibilitando que o LLM erre proporções.
- **Renomeação de BoundingBox para BoundingRetangulo**: Em prol da consistência idiomática do schema com os outros objetos (`BoundingCircular`, `BoundingAreaLivre`), renomearemos também a Message no Proto, ao invés de apenas a chave do campo.
- **Migração do Banco de Imagens**: O código Python será atualizado via Find and Replace para cobrir 100% dos `.box`. Os dados `raw_mapas/*.json` serão modificados de forma persistente através de um script de migração (mudando a chave string JSON).

## Risks / Trade-offs

- **Falhas de Parser e Retrocompatibilidade**: [Risk] JSONs que ainda estiverem referenciando `.box` vão falhar de forma drástica no parser do Protobuf em Python e nas compilações subsequentes do sistema. → **Mitigation**: A implementação incluirá um script robusto de substituição que varrerá todo o projeto `aresta_db` alterando as instâncias nos JSONs persistidos ANTES da execução de qualquer rotina dependente.
