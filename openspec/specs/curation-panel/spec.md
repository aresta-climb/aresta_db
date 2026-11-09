# curation-panel Specification

## Purpose
Define a interface gráfica PySide6 de revisão e curadoria 1 a 1 de betas (`PainelCuradoria`), o Wizard assíncrono de coleta em background (`DialogoColetarBetas` / `WorkerColetaBetas`) e a persistência via comandos do histórico (`CroquiController`).

## Requirements

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

#### Scenario: Curadoria estritamente individual (1 a 1) sem ações destrutivas em lote
- **WHEN** o curador revisa os cards nas seções `betas_nao_revisados` ou `betas_nao_scorados`
- **THEN** a interface MUST fornecer botões individuais de **Aprovar** e **Rejeitar** em cada card e NÃO MUST fornecer botões de aprovação ou limpeza em massa (bulk).
- **THEN** ao clicar em **Aprovar** em um card (seja de `betas_nao_revisados`, `betas_nao_scorados` ou `betas_rejeitados`), o item MUST ser convertido e movido para `escalada.betas`.
- **THEN** ao clicar em **Rejeitar** em um card, o item NÃO MUST ser excluído permanentemente, mas sim movido como `MidiaBeta` para `betas_rejeitados` daquela escalada.

#### Scenario: Execução do Wizard "Coletar Betas..." com progresso
- **WHEN** o usuário clica no botão **"Coletar Betas..."** na aba **Betas**
- **THEN** o sistema MUST abrir um diálogo/wizard permitindo selecionar quais escaladas/setores do croqui terão betas coletados e exibir o progresso da coleta em tempo real.
- **THEN** ao concluir a coleta, os novos candidatos encontrados MUST ser adicionados em `betas_nao_scorados` via comando no `CroquiController` e a aba **Betas** MUST ser atualizada imediatamente.

#### Scenario: Execução do Wizard "Coletar Betas..." em background sem travar a UI
- **WHEN** o usuário clica em **"Iniciar Coleta"** no diálogo **"Coletar Betas..."**
- **THEN** o sistema MUST disparar as consultas HTTP e de scraping em uma `QThread` dedicada (`WorkerColetaBetas`), mantendo o loop de eventos da GUI desimpedido para repintura da janela, atualização da barra de progresso e clique imediato no botão **"Cancelar / Fechar"**.
- **THEN** durante uma inserção em lote de candidatos no `CroquiController`, o `PainelCuradoriaBetas` MUST coalescer as reconstruções visuais para atualizar os cards uma única vez ao término da operação em lote.

#### Scenario: Cancelamento cooperativo durante a coleta em background
- **WHEN** o usuário clica em **"Cancelar / Fechar"** enquanto o `WorkerColetaBetas` está executando
- **THEN** o worker MUST interromper o loop na escalada atual, preservar e injetar em um único comando Undo/Redo os candidatos já coletados até o momento do cancelamento e encerrar a thread sem congelar a janela.

### Requirement: Persistência In-Place
O sistema SHALL realizar todas as mutações de coleta, scoring, aprovação, rejeição e adição manual de betas exclusivamente através de comandos empilhados no histórico global (`CroquiController` / `QUndoCommand`), persistindo os `betas` aprovados no frontmatter dos arquivos `.md` dos setores e mantendo `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados` isolados no arquivo `curadoria_betas.md` vinculado ao `Croqui`.

#### Scenario: Salvamento de vídeos aprovados
- **WHEN** o croqui é salvo no Editor (`CroquiModel.extrair_arquivos_e_serializar`) após aprovações ou rejeições na aba **Betas**
- **THEN** apenas os `betas` aprovados MUST ser gravados nas respectivas escaladas dentro dos arquivos `setor_*.md`, sem poluir os setores com metadados de IA ou itens rejeitados.
- **THEN** as listas `betas_nao_scorados`, `betas_nao_revisados` e `betas_rejeitados` indexadas por `escalada_uid` MUST ser gravadas no arquivo separado `curadoria_betas.md` referenciado em `croqui.yaml`.

#### Scenario: Aprovação e rejeição com suporte a Desfazer/Refazer (Undo/Redo)
- **WHEN** o usuário aprova ou rejeita um candidato na aba **Betas** e em seguida aciona **Desfazer** (`Ctrl+Z`)
- **THEN** o comando no histórico MUST reverter atomicamente tanto a lista `escalada.betas` no setor quanto as listas em `croqui.curadoria_betas.conteudo` para o estado anterior.

### Requirement: Resumo de Betas e Navegação Direta na Ficha da Escalada (Aba Dados)
O sistema SHALL renderizar na ficha da `Escalada` (aba **Dados**) um componente dedicado para visualização/adição rápida de betas aprovados e um resumo do estado de curadoria daquela escalada com botão **"Abrir na Revisão de Betas"**.

#### Scenario: Navegação da ficha da escalada na aba Dados para a aba Betas
- **WHEN** o usuário visualiza uma `Escalada` na aba **Dados** e clica no botão **"Abrir na Revisão de Betas"**
- **THEN** o Editor MUST alternar para a aba **Betas** (`page:betas`) posicionando/focando diretamente na seção daquela escalada.
