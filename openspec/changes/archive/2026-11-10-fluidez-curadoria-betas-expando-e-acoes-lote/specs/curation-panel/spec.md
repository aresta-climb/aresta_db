## MODIFIED Requirements

### Requirement: Interface PySide6 de Curadoria
O sistema SHALL disponibilizar a aba **Betas** (`PainelCuradoriaBetas`) visível na barra lateral da `JanelaPrincipal` do Editor Desktop, apresentando para as escaladas do croqui 4 seções colapsáveis (estilo Expando `▼` / `▶`) na ordem lógica do pipeline (`betas_nao_scorados`, `betas_nao_revisados`, `betas` e `betas_rejeitados`), botões de aprovação/rejeição em lote baseados em limiar de score da LLM exclusivamente na seção `betas_nao_revisados`, botão para abrir o wizard de conexão MCP na seção `betas_nao_scorados` e um Wizard **"Coletar Betas..."** que executa as buscas em paralelo em background (`QThread` + `ThreadPoolExecutor`) mantendo a interface gráfica responsiva (`< 8ms` na thread principal) e preservando a posição de rolagem vertical.

#### Scenario: Apresentação da lista de vídeos e imagens
- **WHEN** o curador abre a aba **Betas** no Editor Desktop
- **THEN** o painel MUST exibir as 4 seções utilizando cabeçalhos Expando clicáveis (`▼` quando expandido, `▶` quando recolhido, sem checkboxes de `QGroupBox`) na seguinte ordem:
  1. **1. Betas Não Scorados (`betas_nao_scorados`)**: candidatos recém-coletados aguardando avaliação da IA, acompanhados de instruções passo a passo, botão **"🔌 Conectar Agente (MCP)..."** (que abre o `DialogoConexaoMcp` do Editor) e botão **"📋 Copiar Prompt MCP"** (que exibe confirmação visual `"✅ Copiado para a área de transferência!"`).
  2. **2. Betas Não Revisados (`betas_nao_revisados`)**: candidatos já avaliados pela IA, ordenados de forma decrescente por `llm_confidence_score` e exibindo a justificativa `llm_reasoning`, os `snippets` e uma barra de ações em lote por limiar de confiança.
  3. **3. Betas Aprovados (`betas`)**: mídias já aprovadas na escalada, permitindo rejeição/remoção.
  4. **4. Betas Rejeitados (`betas_rejeitados`)**: mídias descartadas manualmente ou auto-filtradas na coleta, iniciando **recolhida (`▶`) por padrão** e instanciando seus cards sob demanda (*lazy*) apenas quando o usuário expandir a seção, exibindo fallback visual instantâneo por fonte sem realizar requisições HTTP de thumbnail.
- **THEN** cada card de mídia (`CardBetaCuradoria`) MUST exibir em destaque no topo um cabeçalho/badge identificando a **Via** e o **Setor** (`🧗 Via: <nome_escalada> • 📍 <nome_setor>`), além do badge de sua `FonteMidia.Enum`.

#### Scenario: Curadoria estritamente individual (1 a 1) sem ações destrutivas em lote
- **WHEN** o curador revisa os cards nas seções `betas_nao_scorados`, `betas_nao_revisados`, `betas` ou `betas_rejeitados`
- **THEN** cada card MUST fornecer botões individuais de ação (**Aprovar** / **Rejeitar** ou **Restaurar**) e a seção `1. Betas Não Scorados` NÃO MUST fornecer botões de aprovação ou rejeição em massa.
- **THEN** exclusivamente na seção `2. Betas Não Revisados` (candidatos já avaliados pela LLM), a interface MUST fornecer um seletor numérico de limiar de confiança (padrão **`80`%**) acompanhado dos botões **"✅ Aprovar >= 80%"** e **"❌ Rejeitar < 80%"** (atualizando o rótulo conforme o limiar escolhido), que aprovam ou rejeitam em um único comando Undo/Redo (`CmdMacro`) todos os candidatos não revisados visíveis que atendam ao critério de score.
- **THEN** ao clicar em **Aprovar** ou **Rejeitar** enquanto a página está rolada, o painel NÃO MUST transferir o foco em cascata para os cards inferiores nem rolar a `QScrollArea` para o final da página, preservando a posição vertical do scroll (`verticalScrollBar().value()`) e sem bloquear a thread principal com `worker.wait()`.

#### Scenario: Execução do Wizard "Coletar Betas..." com progresso
- **WHEN** o usuário abre o diálogo **"Coletar Betas..."** na aba **Betas**
- **THEN** no estado inicial o diálogo MUST exibir os botões **"Cancelar"** e **"Iniciar Coleta"**.
- **THEN** enquanto a coleta estiver em execução, o botão **"Iniciar Coleta"** MUST ficar oculto e apenas o botão **"Cancelar Coleta"** MUST ficar visível.
- **THEN** ao concluir a coleta (`100%`), os novos candidatos aprovados pelo filtro MUST ser adicionados em `betas_nao_scorados` e os itens auto-filtrados MUST ser adicionados em `betas_rejeitados` em um único grupo de Undo/Redo no `CroquiController`, e o rodapé do diálogo MUST exibir exclusivamente o botão **"Finalizar"** para fechar o modal.

#### Scenario: Execução do Wizard "Coletar Betas..." em background sem travar a UI
- **WHEN** o usuário clica em **"Iniciar Coleta"** no diálogo **"Coletar Betas..."**
- **THEN** o sistema MUST disparar as buscas das escaladas selecionadas em paralelo através de um `ThreadPoolExecutor` coordenado pela `QThread` (`WorkerColetaBetas`), mantendo o loop de eventos da GUI desimpedido e atualizando a barra de progresso à medida que cada escalada termina.
- **THEN** durante e ao término da inserção em lote de candidatos e auto-rejeitados no `CroquiController`, tanto o `PainelCuradoriaBetas` quanto o `WidgetPainelQualidade` MUST coalescer as reconstruções visuais (`QTimer.singleShot(0)`) para atualizar a interface uma única vez sem congelar no `100%`.

#### Scenario: Cancelamento cooperativo durante a coleta em background
- **WHEN** o usuário clica em **"Cancelar Coleta"** enquanto o `WorkerColetaBetas` está executando
- **THEN** o diálogo MUST solicitar confirmação ao usuário antes de interromper a coleta; se confirmado, o worker MUST cancelar as tarefas pendentes, preservar e injetar em um único comando Undo/Redo os resultados já coletados até o momento e encerrar sem congelar a janela.
