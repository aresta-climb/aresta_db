# Proposta: Otimização de Pipeline de Curadoria, MCP e Coleta de Betas

## Why

A operação real da pipeline de coleta e avaliação de betas em croquis de dezenas a centenas de vias revelou quatro gargalos integrados que degradam latência, confiabilidade e revocação (*recall*):

1. **Lentidão $O(N \cdot \text{Croqui})$ em mutações de lote**: `CroquiController` re-executava varreduras DFS completas da árvore e `CroquiModel` reconstruía o `IndiceUidsModel` centenas de vezes mesmo ao editar coleções de curadoria (`betas_nao_scorados`, `betas_nao_revisados`) sem entidades indexadas por UID, consumindo mais de 5 segundos na thread principal do Qt para 85 vias.
2. **Split-brain no `DespachanteQt`**: quando uma mutação longa já havia iniciado na thread principal do Qt e excedia o timeout único de `10s`, `futuro.cancel()` retornava `False`, fazendo o servidor MCP retornar `TimeoutError` enquanto a mutação era concluída silenciosamente no histórico.
3. **Payload redundante e frágil na pontuação**: pontuar candidatos obrigava o agente a reenviar listas inteiras de `CandidatoMidiaBeta` com `snippets` via `aresta_alterar_em_lote`, desperdiçando tokens e arriscando perda ou corrupção de metadados já residentes em memória.
4. **Baixa revocação no YouTube e filtragem geográfica rígida**: a busca via `ddgs` perdia vídeos reais (como `https://www.youtube.com/watch?v=JZsMiVEl8YA`) por forçar o termo `"escalada"`, sofria com falsos positivos de carrosséis do Yahoo, descartava legendas válidas que citavam apenas a cidade ou apelido do croqui (ou prefixos como `"Complexo"`), não extraía vídeos embutidos em blogs aprovados e não reavaliava itens `[Auto-filtrado: ...]` quando os filtros evoluíam.

## What Changes

- **Frente A — Otimização $O(1)$ de Lote (`CroquiController`, `CroquiModel` e `ferramentas_comandos`)**: reutilização do caminho canônico já validado em `_construir_comandos_para_alvo`, `adicionar_multiplos_repeated` e `alterar_multiplos_repeated_items`; reconstrução seletiva do `IndiceUidsModel` em `CroquiModel` apenas para `CAMPOS_REPEATED_COM_UID_INDEXADO` (`botoes`, `picos`, `setores_ou_grupos`, `setores`, `escaladas`, `enfiadas`) e reindexação condicional nas ferramentas MCP de comandos.
- **Frente B — Blindagem Anti-*Split-Brain* (`DespachanteQt`)**: separação entre tempo limite de fila (`timeout`, cancelável enquanto `PENDING`) e tempo limite máximo de conclusão (`timeout_execucao`, aguardando o resultado real cometido sempre que a tarefa já estiver `RUNNING` na thread principal do Qt).
- **Frente C — Pontuação Atômica e Enxuta (`aresta_pontuar_betas`)**: novo método `CroquiController.pontuar_betas_em_lote`, nova ferramenta MCP `aresta_pontuar_betas` (que recebe apenas `escalada_uid`, `url`, `llm_confidence_score` e `llm_reasoning`, preservando `midia` e `snippets` diretamente da RAM em um único `CmdMacro`), enriquecimento de `pico_cidade` e `croqui_nome` em `aresta_listar_betas_nao_scorados` e atualização da skill `avaliar_betas_croqui`.
- **Frente D — Nova Estratégia de Coleta de Betas**:
  - Separação do YouTube em `ExtratorYouTube` dedicado via endpoint `InnerTube` JSON (`/youtubei/v1/search`) com pacing thread-safe, cobrindo vídeos e Shorts sem forçar `"escalada"`.
  - Remoção da query `"youtube"` e descarte de resultados YouTube no `ExtratorBlog` (`ddgs` focado em Instagram, TikTok, Facebook e Web/Blogs), além da remoção dos módulos órfãos legados `duckduckgo.py` e `vertex.py`.
  - Pulo imediato (zero requisições HTTP) para escaladas com nome placeholder (`Sem nome \d*`, `Projeto \d*`, etc.).
  - Enriquecimento geográfico das queries e de `menciona_contexto_local` com `Pico.cidade`, `Croqui.nome` e `"complexo"` / `"area"` / `"regiao"` / `"nucleo"` em `STOPWORDS_PICO`.
  - Extração leve de vídeos YouTube/Instagram embutidos no HTML exclusivamente para candidatos `FonteMidia.BLOG` já aprovados nos filtros.
  - Reavaliação offline automática de itens `[Auto-filtrado: ...]` em `betas_rejeitados` (`CroquiController.reavaliar_betas_auto_filtrados`) mantendo descartes humanos intocados (sem alterar `beta.proto`), e opção `chk_apenas_sem_coleta` em `DialogoColetarBetas`, mais atualização da skill `coletar_betas_croqui`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability raiz; todas evoluem capabilities existentes no sistema. -->

### Modified Capabilities
- `editor-controle-mcp`: blindagem anti-*split-brain* no `DespachanteQt`, nova ferramenta `aresta_pontuar_betas`, reavaliação offline e propagação de `cidade`/`nome_croqui` na coleta/listagem via MCP, e reindexação condicional nas ferramentas de comando.
- `undo-redo-protobuf`: reuso $O(1)$ de `caminho_res` em operações multi-item no `CroquiController`, reconstrução seletiva do `IndiceUidsModel` no `CroquiModel`, e métodos atômicos `pontuar_betas_em_lote` e `reavaliar_betas_auto_filtrados`.
- `curation-panel`: opção de reexecução seletiva (`chk_apenas_sem_coleta`) e reavaliação offline automática de auto-filtrados no Wizard `DialogoColetarBetas`.
- `media-scraping`: `ExtratorYouTube` via `InnerTube` JSON separado do `ExtratorBlog` (`ddgs` sem YouTube), filtro de nomes placeholder, contexto geográfico ampliado (`Pico.cidade`, `Croqui.nome`, `STOPWORDS_PICO`), extração de embeds em blogs aprovados, normalização de `/embed/` e `/shorts/`, e remoção de `duckduckgo.py` e `vertex.py`.

## Impact

- **Código de Produção**: `editor/models/croqui_model.py`, `editor/controllers/croqui_controller.py`, `editor/mcp/despachante.py`, `editor/mcp/ferramentas_comandos.py`, `editor/mcp/ferramentas_betas.py`, `coleta_de_betas/extratores/{youtube,blog,deduplicador,cliente_http_fake,__init__}.py`, `coleta_de_betas/curadoria/dialogo_coletar_betas.py`.
- **Remoções**: `coleta_de_betas/extratores/duckduckgo.py`, `coleta_de_betas/extratores/duckduckgo_test.py`, `coleta_de_betas/extratores/vertex.py`, `coleta_de_betas/extratores/vertex_test.py`.
- **Skills e Documentação**: `.agents/skills/{avaliar_betas_croqui,coletar_betas_croqui}/SKILL.md`, `editor/controllers/README.md`.
- **Schema Protobuf (`aresta_api`)**: nenhuma alteração em `.proto`; mantém compatibilidade total com `beta.proto` e `croqui.proto`.
