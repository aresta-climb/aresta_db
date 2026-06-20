## Context

Os processos atuais de processamento de um croqui no formato PDF estão espalhados em diferentes rotinas (workflows) manuais: `preparacao_pdf_para_conversao.md`, `converter_pdf_para_croqui.md` e `extrair_informacoes_dos_mapas.md`. 
O objetivo deste documento de design é unificar o fluxo, explorando as capacidades de sub-agentes autônomos introduzidas pelo Antigravity 2.0 (usando comandos como `define_subagent` e `invoke_subagent`).

## Goals / Non-Goals

**Goals:**
- Prover um agente principal (Workflow) capaz de orquestrar ponta a ponta o processo.
- Evitar perda de estado: O Agente deve recuperar facilmente o status em caso de interrupção avaliando a existência de arquivos específicos (implicit state).
- Lidar com falhas: Agentes com problema devem desencadear um evento de "auto-correção", recriando o sub-agente falho até que os limites de tentativa esgotem.
- Otimizar recursos: Rodar processamentos independentes em paralelo (batch) com `invoke_subagent` com arrays.

**Non-Goals:**
- Mudar a modelagem de dados do protobuf para os croquis.
- Alterar como os mapas funcionam no front-end ou de que forma as imagens são manipuladas fora do fluxo de extração.
- Substituir habilidades (skills) se não forem atreladas a esse escopo orquestral (e.g. continuaremos utilizando a `separar_croqui_pdf_em_partes`).

## Decisions

- **Workflow vs. Nova Entidade**: O orquestrador será um workflow no nível de `.agents/workflows/processar_croqui_completo.md`. Isso reaproveita todo o ecossistema Antigravity atual para acionamento, ao invés de codificar uma extensão extra no motor.
- **Estado Implícito**: Não haverá arquivo `status.json`. A avaliação da "Fase" é feita checando se os artefatos obrigatórios existem:
  - `partes.json` não existe -> Executar a Fase 1.
  - Se existe `partes.json` mas faltam arquivos `.md` baseados no JSON -> Executar a Fase 2 (só pros faltantes ou pra todos).
  - Se compilado.md existe e mapas estão extraídos, avançar apropriadamente.
- **Gerenciamento do Workspace de Sub-agentes**: Como os sub-agentes manipulam arquivos num mesmo projeto (croqui) usando skills pré-definidas, o modelo Antigravity de invocar sub-agentes vai utilizar workspaces compartilhados e mutuamente exclusivos, com a salvaguarda de nunca permitirem editar arquivos centrais.
- **Auto-Correção (Auto-heal)**: O orquestrador valida os resultados da Fase. Se falhou (ex: erro no sub-agente), ele não pede desculpa ao usuário imediatamente. Dispara um "retry" lançando o sub-agente novamente. Limite de tentativas: 3. Se falhar na 3ª, pausa e pede intervenção humana.

## Risks / Trade-offs

- **[Risco]** Falha simultânea catastrófica de muitos sub-agentes (e.g., cota de tokens esgotada). -> **[Mitigação]** Retomada resiliente por estado implícito, garantindo que o que já foi salvo com sucesso não será reprocessado ao reiniciar.
- **[Risco]** Alterações simultâneas de sub-agentes com as tools corrompendo arquivos globais. -> **[Mitigação]** Apenas o orquestrador compila arquivos centrais (`croqui.yaml`). Os sub-agentes manipulam estritamente as partes exclusivas (ex. `setor_X.md`) associadas aos seus payloads individuais.
