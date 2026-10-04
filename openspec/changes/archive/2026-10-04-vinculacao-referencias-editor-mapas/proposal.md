# Proposal

## Why

A interação com referências e elementos no Editor de Mapas apresentava comportamentos instáveis:
1. Ao clicar em uma referência após interagir com outra, a referência selecionada apenas "piscava" e a anterior voltava a ficar marcada no mapa, devido a estado residual e ordem de precedência incorreta no fallback de restauração de hover (`remover_destaque_pois`).
2. O botão de associação de elementos usava terminologia em inglês ("Linkar POIs" / "Linkando..."), violando o Princípio I do repositório (Tudo em Português) e gerando confusão de usabilidade.
3. A experiência ao associar pontos de interesse a uma referência precisava ser imediata e clara: ativar a vinculação já destaca em ciano todos os elementos vinculados; clicar em um elemento não vinculado o vincula e destaca em ciano instantaneamente; e clicar em um elemento já vinculado o desvincula e remove o destaque ciano instantaneamente.

## What Changes

- **Renomeação para Português Brasileiro (Princípio I)**:
  - Substituição de `"Linkar POIs"` por `"Vincular Elementos"` nos cards do painel de referências.
  - Substituição do estado ativo `"Linkando..."` por `"Vinculando..."` com fundo azul indicativo.
  - Atualização do texto da barra superior de aviso: `"MODO VINCULAÇÃO - Clique nos elementos do mapa para vinculá-los ou desvinculá-los desta referência. Elementos vinculados ficam em Ciano."`.
  - Atualização dos tooltips e mensagens correlatas.
- **Sincronização entre Seleção e Modo de Vinculação**:
  - Ao ativar `"Vincular Elementos"` em um card, a referência correspondente é automaticamente selecionada no painel (`definir_selecionado(True)`), unificando a referência ativa e a selecionada.
  - Limpeza e redefinição atômica de `referencia_linkagem_ativa` ao trocar de card ou desativar o modo, eliminando restauração indevida da referência anterior no fallback de `remover_destaque_pois`.
- **Reatividade e Feedback Visual Imediato no Mapa**:
  - Ao entrar em modo de vinculação, todos os elementos já pertencentes à referência são destacados em ciano.
  - Ao clicar em um elemento não vinculado no mapa, seu ID é adicionado à referência e seu visual no mapa ganha destaque em ciano imediatamente.
  - Ao clicar em um elemento já vinculado no mapa, seu ID é removido da referência e o destaque ciano é removido imediatamente, retornando à sua cor padrão.

## Capabilities

### New Capabilities
*(Nenhuma nova capacidade introduzida)*

### Modified Capabilities
- `editor-mapas-referencias`: Atualiza os requisitos de vinculação interativa de elementos (substituindo terminologia "Linkagem/POIs" por "Vinculação/Elementos"), formaliza a sincronização estrita entre seleção e vinculação, e define o comportamento determinístico de alternância (toggle) com feedback visual imediato.

## Impact

- **Código Afetado**:
  - `editor/views/widget_painel_referencias.py`: renomeação de botões/rótulos/tooltips, sincronização de clique/toggle com seleção do card.
  - `editor/views/widget_editor_mapas.py`: gerenciamento atômico de `referencia_linkagem_ativa` e `referencia_selecionada`, atualização reativa de destaques no mapa, correção da precedência no fallback de `remover_destaque_pois`.
  - `editor/views/widget_editor_mapas_test.py` e `editor/views/widget_painel_referencias_test.py`: atualização e inclusão de testes TDD cobrindo todos os fluxos de alternância, feedback visual e nomenclatura em português.
- **APIs e Modelos**: Nenhuma alteração de schema Protobuf ou quebra de retrocompatibilidade.
