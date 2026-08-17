---
description: Pipeline automatizado de busca, avaliação distribuída por sub-agentes e extração tipada de betas de escalada
---

# Workflow: Coleta de Betas de Escalada

Este workflow atua como o orquestrador para descoberta, avaliação paralela por sub-agentes nativos do Antigravity e geração tipada do staging de betas das vias de um croqui.

---

## 1. Pré-requisitos e Entradas
- O usuário deve fornecer o caminho do croqui alvo (ex: `database/br_mg_ouro_preto_ouroboulder`).
- As chaves de API opcionais/necessárias no ambiente:
  - `YOUTUBE_API_KEY`: Para a busca na YouTube Data API v3.
  - `VERTEX_PROJECT_ID` e `VERTEX_DATA_STORE_ID`: Para a busca de Instagram via Google Vertex AI Search (Agent Search).

---

## 2. Etapas de Execução do Orquestrador

### Fase 1: Extração Estática das Vias Alvo
1. O orquestrador executa a biblioteca CLI de extração:
   ```bash
   python -m coleta_de_betas.extrair_vias database/<croqui>
   ```
2. O arquivo estaticamente tipado `database/<croqui>/vias_extraidas.yaml` (mensagem `ViasExtraidasCroqui`) é gerado, contendo todas as vias com nome, grau, setor, grupo, pico, cidade e estado.

### Fase 2: Busca Tripla Concorrente
1. O orquestrador executa o runner de busca:
   ```bash
   python -m coleta_de_betas.buscar database/<croqui>
   ```
2. O script executa buscas concorrentes no YouTube, Vertex AI Search e DuckDuckGo, deduplica os resultados e gera `database/<croqui>/candidatos_brutos.yaml` tipado por `BetasPendentes`.

### Fase 3: Avaliação Semântica por Sub-agentes Antigravity
1. O orquestrador registra o sub-agente especialista:
   ```python
   define_subagent(
       name="AvaliadorBetas",
       description="Avalia relevância semântica e correspondência de vídeos e postagens de betas",
       system_prompt="""Você é um especialista em escalada em rocha brasileira.
Sua missão é avaliar mídias candidatas a betas para as vias de um croqui.
Para cada candidato:
- Analise se o nome da via, setor, pico e cidade correspondem ao título, descrição, snippets e miniatura.
- Atribua um score de confiança de 0 a 100 (llm_confidence_score).
- Forneça uma justificativa textual concisa (llm_reasoning).
Retorne a lista com os campos preenchidos em formato YAML."""
   )
   ```
2. O orquestrador divide os candidatos de `candidatos_brutos.yaml` em lotes de 5 a 10 escaladas e dispara chamadas paralelas com `invoke_subagent`.
3. Os sub-agentes avaliam os lotes concorrentemente e retornam os dados pontuados.

### Fase 4: Geração do Arquivo de Staging Binário
1. O orquestrador salva o YAML avaliado e executa o comando de staging:
   ```bash
   python -m coleta_de_betas.salvar_staging database/<croqui>
   ```
2. O arquivo binário `database/<croqui>/betas_pendentes.binarypb` é gerado para consumo no editor desktop e sinalizado no `STATUS_CROQUIS.md`.

### Fase 5: Curadoria e Persistência In-Place
1. O curador abre o Editor desktop (`python editor/main.py`), acessa a aba **Betas**, revisa as miniaturas/scores e aprova os itens desejados.
2. Ao clicar em **Salvar Betas Aprovados**, os dados são gravados diretamente no frontmatter dos arquivos Markdown dos setores (`grupo_*.md`) e o arquivo temporário de staging é removido.
