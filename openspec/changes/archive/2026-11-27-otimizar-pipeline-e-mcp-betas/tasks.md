# Tasks

## 1. Frente A — Otimização O(1) em Lote (`CroquiModel`, `CroquiController` e `ferramentas_comandos`)

- [x] 1.1 Adicionar `CAMPOS_REPEATED_COM_UID_INDEXADO` no `CroquiModel` evitando reconstrução do `IndiceUidsModel` em coleções sem UID (`betas_nao_scorados`, `betas_nao_revisados`, `betas_rejeitados`, etc.) e verificar com testes em `editor/models/croqui_model_test.py`.
- [x] 1.2 Reutilizar `alvo=caminho_res` (`str`) já validado em `_construir_comandos_para_alvo`, `adicionar_multiplos_repeated` e `alterar_multiplos_repeated_items` do `CroquiController`, e validar ganho de latência (`< 200ms` para 85 entradas de curadoria com milhares de rejeitados) e reversibilidade atômica em `editor/controllers/croqui_controller_test.py`.
- [x] 1.3 Tornar condicional a reindexação explícita do `IndiceUidsModel` nas ferramentas de comando em `editor/mcp/ferramentas_comandos.py` e validar via `editor/mcp/ferramentas_comandos_test.py`.

## 2. Frente B — Blindagem Anti-Split-Brain no `DespachanteQt`

- [x] 2.1 Separar timeout de enfileiramento (`timeout`) de timeout máximo de execução (`timeout_execucao`, padrão `60.0s`) em `editor/mcp/despachante.py`, aguardando a conclusão real quando `futuro.cancel()` retornar `False`, e validar todos os cenários (pendente cancelado, execução lenta concluída sem split-brain, e estouro de `timeout_execucao`) em `editor/mcp/despachante_test.py`.

## 3. Frente C — Pontuação Atômica `aresta_pontuar_betas` e Skill `avaliar_betas_croqui`

- [x] 3.1 Implementar `CroquiController.pontuar_betas_em_lote` com validação *fail-fast*, preservação de `midia`/`snippets`/flags da RAM, ordenação decrescente de `betas_nao_revisados` e execução em um único `CmdMacro`, verificando comportamento e falhas em `editor/controllers/croqui_controller_test.py`.
- [x] 3.2 Registrar a ferramenta MCP `aresta_pontuar_betas` e enriquecer `aresta_listar_betas_nao_scorados` com `pico_cidade` e `croqui_nome` em `editor/mcp/ferramentas_betas.py`, validando via `editor/mcp/ferramentas_betas_test.py`.
- [x] 3.3 Atualizar `.agents/skills/avaliar_betas_croqui/SKILL.md` para usar `aresta_pontuar_betas` no Passo 3 e documentar os novos campos em `editor/controllers/README.md`.

## 4. Frente D — Nova Estratégia de Coleta de Betas (YouTube InnerTube, ddgs sem YouTube, Contexto Local, Embeds e Reavaliação Offline)

- [x] 4.1 Remover módulos legados órfãos (`duckduckgo.py`, `duckduckgo_test.py`, `vertex.py`, `vertex_test.py`) e atualizar `coleta_de_betas/extratores/__init__.py` verificando ausência de referências quebradas.
- [x] 4.2 Atualizar `normalizar_url` em `coleta_de_betas/extratores/deduplicador.py` (YouTube `/embed/`, `/v/`, `/shorts/` e Instagram `/reels/`) e ampliar `ClienteHttpProtocolo`/`ClienteHttpFake` em `cliente_http_fake.py` para suportar `headers` no `post`, verificando com `deduplicador_test.py` e `cliente_http_fake_test.py`.
- [x] 4.3 Atualizar `coleta_de_betas/extratores/blog.py`: `STOPWORDS_PICO` (`complexo`, `area`, `regiao`, `nucleo`), `eh_nome_escalada_placeholder`, `limpar_nome_pico_para_query`, `menciona_contexto_local` (`Pico.cidade` + `Croqui.nome`), `extrair_titulo_original_auto_filtrado`, 4 queries no `ExtratorBlog` ignorando YouTube na SERP e extração de vídeos embutidos em páginas `FonteMidia.BLOG` aprovadas, validando via `coleta_de_betas/extratores/blog_test.py`.
- [x] 4.4 Substituir `coleta_de_betas/extratores/youtube.py` pelo extrator `InnerTube` JSON (`/youtubei/v1/search`) com pacing thread-safe, captura de vídeos + Shorts, filtro por contexto local + placeholder e auditoria em `betas_rejeitados`, validando 100% em `coleta_de_betas/extratores/youtube_test.py`.
- [x] 4.5 Implementar `CroquiController.reavaliar_betas_auto_filtrados` (promovendo apenas itens `[Auto-filtrado: ...]` agora válidos e preservando rejeições humanas) e validar via `editor/controllers/croqui_controller_test.py`.
- [x] 4.6 Atualizar `coleta_de_betas/curadoria/dialogo_coletar_betas.py` (propagar `cidade`/`nome_croqui`, `criar_extratores_padrao() -> [ExtratorYouTube(), ExtratorBlog()]`, `chk_apenas_sem_coleta` e reavaliação offline inicial), `editor/mcp/ferramentas_betas.py` (`auto_filtrados_promovidos` e propagação geográfica no `aresta_coletar_betas`) e `.agents/skills/coletar_betas_croqui/SKILL.md`, validando via `dialogo_coletar_betas_test.py` e `ferramentas_betas_test.py`.

## 5. Verificação Integral de Qualidade e Cobertura

- [x] 5.1 Executar `ruff check`, `ruff format --check`, `mypy`, `pytest --cov` (100% de cobertura nos módulos tocados/novos) e a suíte completa `pytest editor coleta_de_betas` com saída verde.

## Workflow follow-up

- Sincronizar delta specs para `openspec/specs/`, validar `openspec validate --specs` e arquivar a mudança em `openspec/changes/archive/2026-11-27-otimizar-pipeline-e-mcp-betas/`.
- Realizar commit seletivo assinado com DCO (`git commit -s`) apenas dos arquivos desta mudança e `git push origin main`.
