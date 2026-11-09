# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente, `DialogoColetarBetas` conecta o botão `btn_iniciar` diretamente a `executar_coleta_sincrona()`, que executa `extrator.buscar(...)` na thread principal do Qt para cada escalada selecionada. Além disso, `PainelCuradoriaBetas` reconstrói todos os widgets `CardBetaCuradoria` (e inicia novas `WorkerProvedorImagem(QThread)`) a cada sinal `repeated_adicionado` disparado individualmente durante um `CmdMacro`.

## Goals / Non-Goals

**Goals:**
- Executar toda a coleta multi-fonte (`ExtratorDuckDuckGo`, `ExtratorBlog`, `ExtratorYouTube`, `ExtratorVertexSearch`) em background via `WorkerColetaBetas(QThread)`.
- Manter o método `executar_coleta_sincrona()` disponível para chamadas diretas em testes unitários rápidos, mas fazer o botão **"Iniciar Coleta"** e o método `iniciar_coleta_assincrona()` operarem via `WorkerColetaBetas`.
- Garantir que todas as mutações no `CroquiModel` / `CroquiController` ocorram exclusivamente na thread principal da GUI ao receber os resultados do worker, agrupadas em um único `CmdMacro("Coletar Betas")`.
- Coalescer `PainelCuradoriaBetas.atualizar_visualizacao()` via `QTimer.singleShot(0, ...)` (ou flag de agendamento) para que N inserções seguidas no mesmo turno do event loop gerem apenas 1 reconstrução de cards, e desconectar/aguardar com segurança qualquer `WorkerProvedorImagem` em andamento antes de destruir um `CardBetaCuradoria`.
- Substituir `duckduckgo-search` por `ddgs` em `pyproject.toml` (grupos `editor` e `pdf`) e em `coleta_de_betas/extratores/blog.py`.

**Non-Goals:**
- Alterar contratos Protobuf (`beta.proto` / `croqui.proto`).

## Decisions

### 1. `WorkerColetaBetas(QThread)` desacoplado de mutações do `CroquiModel`
- **Decisão**: O `WorkerColetaBetas` recebe apenas a lista imutável `selecionadas: list[InfoEscaladaColeta]` e a lista de `extratores: list[ExtratorBetaProtocolo]`. Em `run()`, para cada escalada ele verifica `self.foi_cancelado()`, emite `progresso_alterado(idx, total, info.nome_escalada)`, executa os extratores e deduplica os resultados em memória (`deduplicar_midias`), acumulando `list[tuple[str, list[beta_pb2.CandidatoMidiaBeta]]]`. Ao terminar (ou cancelar), emite `concluido(resultados_acumulados, foi_cancelado)`.
- **Racional**: Modelos Qt/Protobuf conectados a Views nunca devem sofrer mutação fora da thread principal da GUI. Coletar em memória na `QThread` e aplicar no `CroquiController` no slot conectado a `concluido` garante thread-safety total e preserva 1 único comando Undo/Redo.

### 2. Coalescência de `atualizar_visualizacao()` e limpeza segura de `WorkerProvedorImagem`
- **Decisão**:
  1. Em `PainelCuradoriaBetas._ao_mutar_modelo`, em vez de chamar `self.atualizar_visualizacao()` sincronicamente a cada item adicionado em `repeated_adicionado`, agendar uma única atualização com flag `_atualizacao_agendada` e `QTimer.singleShot(0, self._executar_atualizacao_agendada)`.
  2. Em `CardBetaCuradoria`, adicionar um método `encerrar_worker()` chamado por `PainelCuradoriaBetas._limpar_layout()` antes de `deleteLater()`, desconectando o sinal `imagem_carregada` e aguardando/desvinculando o `WorkerProvedorImagem` para evitar warnings/crashes de `QThread: Destroyed while thread is still running`.

### 3. Migração para `ddgs`
- **Decisão**: Atualizar `pyproject.toml` trocando `"duckduckgo-search"` por `"ddgs"` no grupo `pdf` e adicionando `"ddgs"` ao grupo `editor`. Em `coleta_de_betas/extratores/blog.py`, importar `from ddgs import DDGS` (com fallback para `duckduckgo_search` apenas se necessário).

### 4. Institucionalização do Princípio IX nos `AGENTS.md` (`aresta_db`, `aresta_app` e `fixalog`)
- **Decisão**: Como Fakes determinísticos em memória executam em `< 1ms` durante os testes unitários, agentes de IA tendem a acoplar chamadas de rede/I/O ou loops pesados diretamente nos callbacks da thread principal da UI se não houver uma diretriz explícita. Adicionaremos o **Princípio IX (Responsividade Inegociável da UI e Execução Pesada em Background)** em `aresta_db/AGENTS.md`, `aresta_app/AGENTS.md` e `fixalog/AGENTS.md` (bem como referência em `openspec/config.yaml`), tornando obrigatório:
  - Em PySide6 (`aresta_db`): `QThread` + `Signal`s para qualquer I/O de rede, processamento de imagem/PDF/malha ou operação em lote, com mutações no modelo restritas à thread principal e coalescência de sinais visuais.
  - Em Flutter (`aresta_app` e `fixalog`): `Isolate` (`Isolate.run` / `Isolate` dedicado) e operações assíncronas não-bloqueantes para qualquer parsing pesado, geração de EPUB/PDF, criptografia XML-DSig, compressão de mídia ou sincronização em lote.

## Risks / Trade-offs

- **[Risk] Bloqueio de alguns segundos ao clicar em Cancelar enquanto uma requisição HTTP de blog está no meio do `requests.get`** → **Mitigação**: Ao clicar em **"Cancelar"**, desabilitar o botão exibindo `"Cancelando..."` enquanto o worker finaliza a requisição atual (timeout curto) e, caso o usuário feche a janela, desconectar e aguardar de forma segura sem corromper o estado do modelo.
