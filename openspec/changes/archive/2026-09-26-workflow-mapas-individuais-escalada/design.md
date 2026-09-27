# Design Técnico: Workflows de Agente para Mapas Individuais de Escalada

## Context

O pipeline de agentes autônomos (`.agents/workflows/processar_croqui_completo.md`) opera em 3 fases:
1. `SeparadorPDF` cria `partes.json` e reparte o PDF em arquivos menores em `raw_pdf_contents/`.
2. `ConversorMarkdown` transcreve cada parte para um arquivo `.md` com YAML Frontmatter.
3. `ExtratorMapas` roda OCR e cataloga pontos de interesse em `raw_mapas/`.

Com a introdução de `Escalada.mapas` (1.0 MP @ WebP Q85), o pipeline precisa estender a Fase 2 (associação heurística) e a Fase 3 (OCR em mapas de escalada), além de delegar a compressão para `preparar_submissao_lib.py`.

## Goals / Non-Goals

**Goals:**
- Ensinar a skill `converter_parte_croqui_para_markdown` a associar fotos de detalhe de vias/boulders diretamente em `escaladas[].mapas`.
- Fazer `scripts/preparar_extracao_de_mapas.py` e `scripts/finalizar_mapas.py` suportarem `escaladas[].mapas` com OCR e injeção de pontos.
- Fazer `preparar_submissao_lib.py` aplicar automaticamente 1.0 MP @ Q85 em mapas de escalada e 2.5 MP @ Q85 em mapas de setor ao migrar de `raw_pdf_contents/`.
- Manter 100% de cobertura nos testes do backend e compatibilidade retroativa.

**Non-Goals:**
- Alterar o schema Protobuf (`aresta_api`), que já suporta `Escalada.mapas`.
- Alterar o aplicativo móvel (`aresta_app`), que já consome mapas de escalada no carrossel unificado.
- Exigir que subagentes LLM façam o redimensionamento de imagens ou cálculos matemáticos de pixels.

## Decisions

### 1. Separação de Responsabilidades: Agente Heurístico vs. Compilador Determinístico
- **Decisão**: O subagente LLM apenas detecta semanticamente se uma imagem é panorâmica de setor (`Setor.mapas`) ou de detalhe de escalada (`escaladas[].mapas`) e aponta o caminho original em `raw_pdf_contents/imagens/...`. A compressão e redimensionamento ficam a cargo do `preparar_submissao_lib.py`.
- **Alternativa Considerada**: Fazer o agente executar ferramentas CLI de redimensionamento antes de escrever o Markdown.
- **Justificativa**: Evita alucinações de argumentos CLI por LLMs, economiza chamadas de ferramentas e garante aplicação uniforme e determinística dos limites de 1.0 MP e 2.5 MP.

### 2. Metadados de OCR Vinculados em `raw_mapas/`
- **Decisão**: `preparar_extracao_de_mapas.py` insere campos no JSON: `"pertence_a_escalada": true`, `"escalada_nome": "..."` e `"escalada_indice": N`.
- **Alternativa Considerada**: Criar subpastas separadas `raw_mapas_escaladas/`.
- **Justificativa**: Manter um único diretório `raw_mapas/` permite que o subagente `ExtratorMapas` processe todos os mapas com as mesmas ferramentas sem alterar os limites de lote (*batching* de 8 mapas por agente).

### 3. Compressão em `preparar_submissao_lib.py` via `comprimir_imagem_para_bytes_webp`
- **Decisão**: Substituir `shutil.copy2` por `comprimir_imagem_para_bytes_webp` ao migrar arquivos de `raw_pdf_contents/` para `imagens/`, usando `AREA_MAXIMA_ESCALADA` e `QUALIDADE_WEBP_ESCALADA` quando o mapa estiver no contexto de escalada.
- **Justificativa**: Garante que nenhuma imagem pesada ou desnecessariamente grande vinda do PDF vá para produção ou para o repositório.

## Risks / Trade-offs

- **[Risco de Falso Positivo na Associação de Mapa]** $\rightarrow$ *Mitigação*: A skill orienta que imagens com duas ou mais rotas numeradas são estritamente mapas de setor (`Setor.mapas`). Imagens só vão para a escalada se focarem exclusivamente nela. Além disso, o usuário valida visualmente no editor (`python -m editor.main`) no checkpoint entre a Fase 2 e a Fase 3.
- **[Risco de Imagens Duplicadas]** $\rightarrow$ *Mitigação*: O script `preparar_submissao_lib.py` verifica existência por hash e reutiliza o mesmo arquivo se o mesmo caminho de imagem for referenciado mais de uma vez.
