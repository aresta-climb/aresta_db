# Tasks

## 1. Execução Fora da Thread Principal do Qt no ServidorMCP

- [x] 1.1 Adicionar teste comportamental em `editor/mcp/servidor_test.py` validando que ferramentas registradas com `executar_na_thread_qt=False` executam seu manipulador sem passar pelo `DespachanteQt.executar` e verificar que falha antes da implementação (Red)
- [x] 1.2 Implementar o parâmetro `executar_na_thread_qt: bool = True` em `DefinicaoFerramentaMcp` e `ServidorMCP.registrar_ferramenta` em `editor/mcp/servidor.py` e verificar que `pytest editor/mcp/servidor_test.py` passa com 100% de cobertura (Green)

## 2. Ferramentas MCP de Coleta em Background e Listagem Paginada de Betas

- [x] 2.1 Criar `editor/mcp/ferramentas_betas_test.py` cobrindo todos os comportamentos de `aresta_coletar_betas` (coleta rápida concluída no long-polling, coleta em micro-lotes com retorno `em_andamento`, consulta de `status`, `cancelar` preservando progresso incremental, filtros `apenas_sem_coleta`, `alvo_setor` e `escaladas_uids`, validação de erros fail-fast) e de `aresta_listar_betas_nao_scorados` (paginação `offset`/`limite`, filtro por `alvo_setor`, enriquecimento de metadados e omissão de `betas_rejeitados`) usando buscadores fakes determinísticos e verificar que falha antes da implementação (Red)
- [x] 2.2 Implementar `editor/mcp/ferramentas_betas.py` (`GerenciadorColetaBetasMcp`, `registrar_ferramentas_betas`) e integrá-lo em `editor/legacy_views/area_principal.py`, verificando que `pytest editor/mcp/ferramentas_betas_test.py` passa com 100% de cobertura (Green)

## 3. Skills de Domínio e Orientações na Aba Betas

- [x] 3.1 Criar `.agents/skills/coletar_betas_croqui/SKILL.md` com instruções completas para coleta de betas via MCP em croquis pequenos e de grande porte (1.000+ vias) e atualizar `.agents/skills/avaliar_betas_croqui/SKILL.md` para usar `aresta_listar_betas_nao_scorados`, verificando via `pytest editor/mcp/ferramentas_conhecimento_test.py` que a nova skill é listada e lida pelo servidor MCP
- [x] 3.2 Atualizar `INSTRUCOES_MCP_AVALIACAO` em `coleta_de_betas/curadoria/painel_curadoria.py` (e `coleta_de_betas/curadoria/painel_curadoria_test.py`) para mencionar também a skill `coletar_betas_croqui` e verificar que os testes do painel passam
