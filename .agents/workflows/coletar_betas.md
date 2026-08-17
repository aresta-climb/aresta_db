---
description: Pipeline automatizado de busca e extração de betas de escalada (YouTube, Vertex AI, DuckDuckGo) com IA e curadoria
---

# Workflow: Coleta de Betas de Escalada

Este workflow atua como o orquestrador para descoberta, avaliação por inteligência artificial e geração do staging de vídeos e postagens demonstrando os betas das vias de um croqui.

---

## 1. Pré-requisitos e Entradas
- O usuário deve fornecer o caminho do croqui alvo (ex: `database/br_mg_ouro_preto_ouroboulder`).
- As chaves de API opcionais/necessárias no ambiente:
  - `YOUTUBE_API_KEY`: Para a YouTube Data API v3.
  - `VERTEX_PROJECT_ID` e `VERTEX_DATA_STORE_ID`: Para a busca de Instagram via Vertex AI Search (Agent Search).

---

## 2. Etapas de Execução

### Fase 1: Leitura das Escaladas Alvo
1. O agente orquestrador lê os arquivos `.md` do croqui para listar todas as vias e boulders (nome da via, grau, setor e pico).
2. Agrupa as vias em lotes para processamento eficiente.

### Fase 2: Busca Tripla Concorrente (Extração)
1. Para cada via do croqui, executa a busca paralela em 3 fontes:
   - **YouTube API v3** (`coleta_de_betas.extratores.youtube.ExtratorYouTube`).
   - **Vertex AI Search** (`coleta_de_betas.extratores.vertex.ExtratorVertexSearch`).
   - **DuckDuckGo** (`coleta_de_betas.extratores.duckduckgo.ExtratorDuckDuckGo`).
2. Consolida os resultados brutos aplicando deduplicação normalizada com `coleta_de_betas.extratores.deduplicador.deduplicar_midias`.

### Fase 3: Avaliação Semântica por IA (Sub-agentes / Batch)
1. Envia os títulos, links, snippets e **URLs de thumbnail** dos candidatos para o modelo LLM através de `coleta_de_betas.inteligencia.avaliador.avaliar_candidatos`.
2. A IA avalia a probabilidade de correspondência e atribui um `llm_confidence_score` (0 a 100) e uma justificativa (`llm_reasoning`), sem tentar extrair resumos forçados de crux.

### Fase 4: Geração do Arquivo de Staging
1. Agrupa os candidatos por escalada na mensagem raiz `BetasPendentes`.
2. Salva o arquivo binário `database/<croqui>/betas_pendentes.binarypb`.
3. Emite um resumo para o usuário informando quantas mídias candidatas foram encontradas.

### Fase 5: Curadoria e Persistência
1. O curador abre o Editor desktop (`python editor/main.py`), seleciona a aba **Betas**, revisa as thumbnails e aprova os itens desejados.
2. Ao salvar, os betas aprovados são injetados diretamente nos arquivos Markdown de cada setor (`grupo_*.md`), limpando o staging e permitindo a compilação final para `compilado.binarypb`.
