# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente:
1. O `ServidorMCP` (`editor/mcp/servidor.py`) executa todos os manipuladores de ferramentas dentro de `self.despachante.executar(ferramenta.manipulador, argumentos)`, que bloqueia a thread principal do Qt durante toda a execução e possui timeout fixo de `10.0s` (`editor/mcp/despachante.py`). Além disso, a ponte `stdio` (`editor/mcp/bridge.py`) possui timeout HTTP de `30.0s`.
2. A coleta de betas (`ExtratorBlog` em `coleta_de_betas/extratores/blog.py`) realiza 5 buscas web por escalada. Para um croqui de 1.000+ vias, são 5.000+ requisições HTTP que levam de 10 a 20 minutos.
3. Na avaliação (`avaliar_betas_croqui`), a leitura de `curadoria_betas.conteudo` via `aresta_obter_arvore` serializa todas as escaladas e todos os `betas_rejeitados` (que acumulam dezenas de URLs auto-filtradas por via), gerando payloads de vários megabytes em croquis grandes e exigindo chamadas adicionais de `aresta_obter_arvore(alvo=escalada_uid)` para descobrir nome, grau, modalidade e setor.

## Goals / Non-Goals

**Goals:**
- Permitir que o agente inicie, consulte o progresso e cancele a coleta multi-fonte de betas 100% via MCP (`aresta_coletar_betas`) sem bloquear a thread principal do Qt (cumprindo o orçamento de meio frame `< 8ms` do Princípio IX do `AGENTS.md`) e sem estourar os timeouts do `DespachanteQt` (`10s`) ou da ponte `stdio` (`30s`).
- Garantir persistência incremental em memória por micro-lotes (ex.: a cada 10 escaladas coletadas) no `CroquiController`, para que coletas longas (1.000+ vias) atualizem a UI em tempo real e jamais percam progresso em caso de cancelamento ou interrupção.
- Fornecer leitura paginada e já enriquecida dos candidatos pendentes (`aresta_listar_betas_nao_scorados`), eliminando o tráfego de `betas_rejeitados` e as N chamadas extras para buscar metadados das escaladas.
- Disponibilizar a nova skill `coletar_betas_croqui` e atualizar `avaliar_betas_croqui`.

**Non-Goals:**
- Alterar a lógica de busca ou os filtros semânticos do `ExtratorBlog`.
- Automatizar a aprovação ou rejeição final (que permanece exclusivamente humana na seção `2. Betas Não Revisados` da aba **Betas**).

## Decisions

### 1. Suporte a `executar_na_thread_qt: bool = True` em `DefinicaoFerramentaMcp`
- **Decisão**: Adicionar o atributo booleano `executar_na_thread_qt: bool = True` em `DefinicaoFerramentaMcp` e no método `ServidorMCP.registrar_ferramenta`. Quando `executar_na_thread_qt=True` (padrão), o `ServidorMCP` mantém o comportamento atual (`self.despachante.executar(ferramenta.manipulador, argumentos)`). Quando `executar_na_thread_qt=False`, o `ServidorMCP` invoca `ferramenta.manipulador(argumentos)` diretamente na thread HTTP do Uvicorn, cabendo à ferramenta usar `servidor.despachante.executar(...)` pontualmente apenas para ler ou gravar no `CroquiModel` / `CroquiController`.
- **Alternativas consideradas**: Aumentar o timeout do `DespachanteQt` para minutos. Descartado porque rodar I/O de rede dentro do `DespachanteQt` congelaria a thread principal do Qt, violando frontalmente o Princípio IX do `AGENTS.md`.

### 2. Gerenciador de Coleta em Background com Micro-Lotes e Long-Polling (`aresta_coletar_betas`)
- **Decisão**: Criar `GerenciadorColetaBetasMcp` em `editor/mcp/ferramentas_betas.py`, registrado com `executar_na_thread_qt=False`.
  - **Leitura inicial (< 2ms na UI thread)**: Usa `despachante.executar` para ler as escaladas do croqui (filtradas por `alvo_setor`, `escaladas_uids` e `apenas_sem_coleta=True`, onde uma escalada é considerada "já com coleta" se possuir betas aprovados em `Escalada.betas` ou qualquer item em `betas_nao_scorados`, `betas_nao_revisados` ou `betas_rejeitados`).
  - **Execução em Background e Micro-Lotes (`tamanho_lote_flush: int = 10`)**: Uma thread daemon com `ThreadPoolExecutor` executa a coleta das escaladas. A cada `tamanho_lote_flush` escaladas concluídas (ou ao final), faz flush atômico no `CroquiController` via `despachante.executar` (< 2ms na UI thread), gravando `adicionar_candidatos_nao_scorados` e `adicionar_betas_rejeitados_lote`.
  - **Long-Polling Seguro (`aguardar_segundos: float = 15.0`, limitado a `[0.0, 20.0]`)**: Nas ações `"iniciar"` e `"status"`, aguarda um `threading.Event` de conclusão por até `aguardar_segundos` fora da thread do Qt. Se terminar dentro da janela, já retorna `status: "concluido"`; caso contrário, retorna `status: "em_andamento"` com os contadores atualizados.

### 3. Consulta Paginada e Enriquecida (`aresta_listar_betas_nao_scorados`)
- **Decisão**: Registrar `aresta_listar_betas_nao_scorados` em `editor/mcp/ferramentas_betas.py` (com `executar_na_thread_qt=True`, pois é uma leitura em memória ultrarrápida `< 2ms`).
  - Percorre `curadoria_betas.conteudo.escaladas` filtrando apenas entradas com `len(betas_nao_scorados) > 0` (e opcionalmente por `alvo_setor`).
  - Aplica paginação `offset` (padrão `0`) e `limite` (padrão `25`, máx. `100`).
  - Para cada item da página, cruza em $O(1)$ com os metadados da escalada no `Croqui` (`indice_curadoria`, `escalada_uid`, `nome`, `dificuldade`, `modalidade`, `setor_uid`, `setor_nome`, `pico_nome`, `conquistadores`, `betas_nao_scorados` e `betas_nao_revisados` existentes para permitir merge direto), omitindo `betas_rejeitados`.

## Risks / Trade-offs

- **[Risk] Concorrência se o usuário ou agente chamar `iniciar` enquanto uma coleta já estiver em andamento** → **Mitigation**: Se já houver um job em andamento quando `acao="iniciar"` for chamado, o gerenciador não inicia um segundo job duplicado; ele aguarda até `aguardar_segundos` no job ativo e retorna seu status atual.
- **[Risk] Croqui fechado ou trocado durante uma coleta em background** → **Mitigation**: O flush incremental verifica se o `uid` da escalada ainda existe no `CroquiModel` ativo antes de gravar no `CroquiController` e interrompe cooperativamente caso o modelo tenha mudado.
