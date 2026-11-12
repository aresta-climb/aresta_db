# Proposal

## Why

Atualmente, a etapa de coleta de candidatos a beta (`ExtratorBlog` / `WorkerColetaBetas`) só pode ser disparada manualmente pela interface gráfica do Editor Aresta (botão `🔍 Coletar Betas...`), impedindo que agentes conectados via MCP executem o fluxo de ponta a ponta autonomamente. Além disso, em croquis de grande porte (1.000+ vias, equivalentes a 5.000+ buscas web e dezenas de milhares de itens em `betas_rejeitados`), uma chamada síncrona única estouraria o timeout da ponte MCP (`30s` em `bridge.py` / `10s` em `DespachanteQt`) e a leitura integral de `curadoria_betas.conteudo` trafegaria megabytes desnecessários de `betas_rejeitados`.

## What Changes

- Suporte no `ServidorMCP` para ferramentas cujo manipulador gerencia seu próprio ciclo fora da thread principal do Qt (`executar_na_thread_qt: bool = True` por padrão, podendo ser `False` quando a ferramenta coordena trabalho pesado em background e usa `DespachanteQt` apenas nas leituras e gravações atômicas).
- Novo módulo `editor/mcp/ferramentas_betas.py` (com suíte espelhada `editor/mcp/ferramentas_betas_test.py`) expondo duas novas ferramentas MCP no Editor Aresta:
  - `aresta_coletar_betas`: Gerencia a coleta multi-fonte em background (`acao`: `"iniciar"`, `"status"`, `"cancelar"`) com filtros (`alvo_setor`, `escaladas_uids`, `apenas_sem_coleta=True`), persistência incremental em micro-lotes (ex.: a cada 10 escaladas concluídas via `CroquiController` na thread do Qt em `< 2ms`) e *long-polling* configurável (`aguardar_segundos`, limitado a `20s`) fora da thread principal do Qt.
  - `aresta_listar_betas_nao_scorados`: Retorna de forma paginada (`offset`, `limite`) e enxuta apenas as escaladas que possuem itens pendentes em `betas_nao_scorados`, já enriquecidas com os metadados da escalada (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_nome`, `pico_nome`, `conquistadores`) e sem trafegar `betas_rejeitados`.
- Criação da nova skill `.agents/skills/coletar_betas_croqui/SKILL.md` com instruções passo a passo para coletar betas via MCP tanto em croquis pequenos quanto em croquis de 1.000+ vias.
- Atualização da skill `.agents/skills/avaliar_betas_croqui/SKILL.md` e das instruções na aba **Betas** (`painel_curadoria.py`) para utilizar `aresta_listar_betas_nao_scorados` paginado e referenciar `coletar_betas_croqui`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-controle-mcp`: Adiciona as ferramentas `aresta_coletar_betas` (coleta assíncrona em background com checkpoint incremental por micro-lote e long-polling fora da UI thread) e `aresta_listar_betas_nao_scorados` (consulta paginada e enriquecida de candidatos pendentes sem `betas_rejeitados`).
- `avaliador-betas-subagente`: Adiciona a skill dedicada `coletar_betas_croqui` para coleta via MCP em escala (1.000+ vias) e atualiza a skill `avaliar_betas_croqui` para leitura paginada via `aresta_listar_betas_nao_scorados`.

## Impact

- `editor/mcp/servidor.py` e `editor/mcp/servidor_test.py`: Suporte a `executar_na_thread_qt: bool = True` em `DefinicaoFerramentaMcp`.
- `editor/mcp/ferramentas_betas.py` e `editor/mcp/ferramentas_betas_test.py`: Implementação e testes comportamentais (com fakes determinísticos de busca, zero mocks internos) de `aresta_coletar_betas` e `aresta_listar_betas_nao_scorados`.
- `editor/legacy_views/area_principal.py`: Registro de `registrar_ferramentas_betas` ao abrir um croqui.
- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`: Atualização do texto orientativo de MCP na aba Betas.
- `.agents/skills/coletar_betas_croqui/SKILL.md` e `.agents/skills/avaliar_betas_croqui/SKILL.md`: Documentação e instruções para agentes.
