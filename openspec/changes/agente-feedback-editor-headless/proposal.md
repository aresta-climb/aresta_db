# Proposal

## Why

O resolvedor automatizado de feedbacks (`ai-feedback-solver.yml` / `serving/agente_feedback`) opera hoje em um paradigma *one-shot* que entrega ao modelo apenas os arquivos `.md` pré-filtrados e exige a reescrita textual completa de cada arquivo. Isso impede o agente de resolver feedbacks estruturais reais — como a Issue #108 (criar um novo setor e migrar uma via preservando seu `UID` e referências) —, consome tokens excessivos de saída, dispara execuções duplicadas na abertura de Issues rotuladas e desperdiça todo o ferramental transacional e multimodal que o Editor Aresta já possui via MCP.

## What Changes

- **3ª Porta Oficial de Entrada do Editor (Modo Headless MCP)**: Introduz o `HeadlessWorkspace` e a sessão oficial `SessaoEditorHeadless` (acessível tanto via API Python em processo quanto via CLI `editor/main.py --headless <caminho_croqui>`), executando `CroquiModel`, `CroquiController`, `MapasController` e `ServidorMCP` sobre `QGuiApplication` (`QT_QPA_PLATFORM=offscreen`, zero `QWidget`), persistindo fontes em `database/<id>` e compilando (`deploy`) em diretório temporário descartável sem sujar `generated/` ou `STATUS_CROQUIS.md`.
- **Registro Canônico Unificado de Ferramentas MCP**: Extrai o registro completo das ferramentas MCP de dentro de `JanelaPrincipal` para uma fábrica compartilhada entre os 3 modos oficiais do Editor (Padrão Experimental, Local Mode e Headless Mode).
- **Grupo de Dependências `editor_headless` Herdado por `editor`**: Reorganiza `pyproject.toml` criando o grupo enxuto `editor_headless` (contendo `validador`, `pyside6-essentials`, `pymupdf` e núcleo MCP) e fazendo o grupo `editor` herdar `{ include-group = "editor_headless" }`, evitando duplicação e mantendo o `uv sync` da GitHub Action em poucos segundos.
- **Deduplicação de Disparo na GitHub Action**: Ajusta `.github/workflows/ai-feedback-solver.yml` para evitar execução dupla simultânea (`opened` + `labeled`) e adiciona controle de `concurrency` por Issue/PR.
- **BREAKING (Interno em `serving/agente_feedback`) — Agente com *Warm-Start*, *Function Calling* em Processo e Skill de Resolução**: Realiza corte limpo substituindo a reescrita bruta de arquivos `.md`/`.yaml` e a renderização ansiosa de réguas estáticas por um loop de *Function Calling* acoplado em memória à `SessaoEditorHeadless`, inicializado com um pacote *Warm-Start* (skill/instruções base do Editor, índice estrutural completo do croqui com `UID`s, subárvore foco e captura de tela) e ferramenta finalizadora `finalizar_resolucao` — resolvendo casos diretos em **1 turno de IA** e casos multi-etapa (criação de setor + `aresta_migrar_escalada`, leitura de skills ou inspeção sob demanda com `aresta_renderizar_mapa`) em até `max_turnos` turnos.
- **Três Camadas de Segurança (Desistência Voluntária, *Circuit Breaker* e Guarda de Mudança Maior)**: Permite ao agente desistir proativamente (`acao="nao_acionavel"`), impõe teto rígido de turnos para proteger a cota gratuita do AI Studio e valida deterministicamente o impacto via `calcular_diff_pull_request` (`diff_croqui_pr_lib`), exigindo confirmação de mantenedor via `/ai-fix` antes de abrir PR caso haja exclusão líquida de entidades, criação de mais de 1 setor, alteração em mais de 5 escaladas ou mudança de `id`/`publicar_croqui`.

## Capabilities

### New Capabilities
- `editor-headless-mode`: Terceiro modo oficial de inicialização e operação sem janelas (`HeadlessWorkspace`, `SessaoEditorHeadless` e CLI `--headless`) para controle integral do Editor Aresta via MCP em memória ou `stdio`, com compilação isolada em diretório temporário.

### Modified Capabilities
- `editor-controle-mcp`: Unificação do registro canônico de ferramentas MCP entre os modos gráfico e *headless*, suportando despacho direto em memória sem dependência obrigatória de widgets visuais.
- `gerenciamento-dependencias-uv`: Adição do grupo de dependências `editor_headless` e herança pelo grupo `editor` sem duplicação de pacotes.
- `agente-ia-resolucao-feedbacks-croqui`: Evolução do fluxo de resolução de feedbacks para deduplicação de eventos, operação sobre o Editor Headless com *Warm-Start* de 1 turno para casos diretos, *multi-turn* com *Circuit Breaker*, desistência voluntária e guarda determinística de Mudança Maior.

## Impact

- **Editor (`editor/`)**: `editor/core/workspace.py` (`HeadlessWorkspace`), novo módulo `editor/mcp/sessao_headless.py` (e registro unificado em `editor/mcp/`), `editor/legacy_views/area_principal.py` e `editor/main.py` (`--headless`).
- **Agente de Feedback e Skills (`serving/agente_feedback/`, `.agents/skills/`)**: Substituição de `cliente_gemini_feedback.py` (+ `cliente_gemini_feedback_fake.py`), `orquestrador_resolucao_feedback.py`, remoção de `renderizador_regua_mapa.py` legado em favor de `aresta_renderizar_mapa` nativo do Editor, atualização de `serving/resolver_feedback_ia.py` e criação de skill dedicada de resolução de feedbacks via Editor MCP.
- **CI/CD e Dependências (`.github/workflows/`, `pyproject.toml`, `uv.lock`)**: Atualização de `ai-feedback-solver.yml` (`--only-group editor_headless`, deduplicação de gatilho e `concurrency`) e grupos em `pyproject.toml`.
