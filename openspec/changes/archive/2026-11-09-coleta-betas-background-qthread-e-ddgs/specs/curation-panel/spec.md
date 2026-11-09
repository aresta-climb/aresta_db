# Spec Delta

## MODIFIED Requirements

### Requirement: Interface PySide6 de Curadoria
O sistema SHALL disponibilizar a aba **Betas** (`PainelCuradoriaBetas`) visível na barra lateral da `JanelaPrincipal` do Editor Desktop, apresentando para as escaladas do croqui 4 seções expansíveis correspondentes ao ciclo de vida dos betas (`betas_nao_revisados`, `betas_nao_scorados`, `betas` e `betas_rejeitados`) e um Wizard **"Coletar Betas..."** que executa as buscas de rede em uma thread de background (`QThread`) mantendo a interface gráfica responsiva e coalescendo as atualizações visuais em lote.

#### Scenario: Apresentação da lista de vídeos e imagens
- **WHEN** o curador abre a aba **Betas** no Editor Desktop
- **THEN** o painel MUST exibir as 4 seções expansíveis:
  1. **Não Revisados (`betas_nao_revisados`)**: candidatos já avaliados pela IA, ordenados de forma decrescente por `llm_confidence_score` e exibindo a justificativa `llm_reasoning` e os `snippets`.
  2. **Não Scorados (`betas_nao_scorados`)**: candidatos recém-coletados aguardando avaliação da IA, acompanhados de instruções claras na UI para acionar a skill de scoring via agente MCP conectado.
  3. **Betas Aprovados (`betas`)**: mídias já aprovadas na escalada, permitindo edição manual ou remoção/rejeição.
  4. **Betas Rejeitados (`betas_rejeitados`)**: mídias descartadas anteriormente, exibidas com opção de restauração.
- **THEN** cada card de mídia MUST carregar sua miniatura de pré-visualização de forma assíncrona via cache persistente (`ProvedorImagemAresta`) com fallback temático caso a imagem não esteja disponível, encerrando com segurança as threads de download ao substituir ou destruir cards.

#### Scenario: Execução do Wizard "Coletar Betas..." em background sem travar a UI
- **WHEN** o usuário clica em **"Iniciar Coleta"** no diálogo **"Coletar Betas..."**
- **THEN** o sistema MUST disparar as consultas HTTP e de scraping em uma `QThread` dedicada (`WorkerColetaBetas`), mantendo o loop de eventos da GUI desimpedido para repintura da janela, atualização da barra de progresso e clique imediato no botão **"Cancelar / Fechar"**.
- **THEN** durante uma inserção em lote de candidatos no `CroquiController`, o `PainelCuradoriaBetas` MUST coalescer as reconstruções visuais para atualizar os cards uma única vez ao término da operação em lote.

#### Scenario: Cancelamento cooperativo durante a coleta em background
- **WHEN** o usuário clica em **"Cancelar / Fechar"** enquanto o `WorkerColetaBetas` está executando
- **THEN** o worker MUST interromper o loop na escalada atual, preservar e injetar em um único comando Undo/Redo os candidatos já coletados até o momento do cancelamento e encerrar a thread sem congelar a janela.
