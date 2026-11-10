# Proposal

## Why

As inspeções técnicas, intervenções de manutenção e o controle de estoque de proteções realizados pela ACEC-MG e pela Rupestre da Lapa Aventuras (GTEL) na Gruta da Lapinha entre julho e novembro de 2026 encontram-se distribuídos em dois documentos com recortes temporais distintos: o Relatório Consolidado no Google Docs (corte em `07/09/2026`) e o Relatório de Estoque e Utilização de Proteções ACEC em PDF (corte em `09/11/2026`). Precisamos unificar o histórico técnico e de estoque no Google Docs e integrar ao croqui da Gruta da Lapinha no Aresta (`br_mg_lagoa_santa_gruta_da_lapinha`) apenas as informações relevantes para o escalador na rocha (datas de manutenção, créditos, interdição da via `91` e avisos objetivos de segurança sem alarmismo).

## What Changes

- **Atualização do Croqui `br_mg_lagoa_santa_gruta_da_lapinha` no Aresta**:
  - **Créditos do Croqui (`croqui.yaml` e `creditos.md`)**: Preencher o campo estruturado `creditos` em `croqui.yaml` com os autores do croqui original (*Eustáquio Macedo Melo Júnior*, *Daniel Ferreira Mariano*) e as entidades responsáveis pelas revitalizações em 2026+ (*ACEC-MG*, *Rupestre da Lapa Aventuras*), além de atualizar `creditos.md` com a equipe técnica do GTEL e o link direto para o Relatório Consolidado no Google Docs.
  - **Datas de Manutenção (`data_manutencao`) e Limpeza de Redundâncias**:
    - `76. Cariocas não dizem Uai`: preencher `data_manutencao: 05/09/2026`.
    - `78. Aceitam-se Sugestões`: preencher `data_manutencao: 12/10/2026` (mantendo `quantidade_protecoes_intermediarias: 7` e removendo o texto redundante de manutenção da `descricao`).
    - `86. Bigode Limpo`: preencher `data_manutencao: 12/10/2026`.
    - `87. Bigode de Cristo`: preencher `data_manutencao: 12/10/2026` (mantendo na `descricao` apenas o alerta sobre o bico de pedra instável próximo à parada).
    - `99. Vale Perdido`: preencher `data_manutencao: 12/10/2026`.
  - **Interdição de Segurança (`91. Trombeta Acéfala`)**:
    - Preencher `quantidade_protecoes_parada: 2` e `descricao` indicando interdição por bloco instável no trecho de colocação de peça móvel.
  - **Avisos Práticos de Segurança ("Beta de Segurança" em tom não alarmista)**:
    - `02. Favo de Mel`: complementar que é via mista exigindo peças móveis no meio e atenção a abelhas.
    - `47. Sobrevibrenf´s`: proteções espaçadas, especialmente entre a 1ª e a 2ª proteção.
    - `48. Sobreviventes`: atenção na segurança nos primeiros lances (até a 3ª proteção) devido à saliência de rocha abaixo.
    - `49. Scarface`: proteções espaçadas e atenção na segurança entre a 1ª e a 2ª proteção (sem alterar `extensao`).
    - `53. Come Quieto`: informar quebra de agarra na saída e parada simples antes do teto.
    - `55. Arranca Couro`: atenção na segurança entre a 1ª e a 2ª proteção (lance esticado próximo à base).
    - `76. Cariocas não dizem Uai`: lance mais esticado no crux (entre a 6ª e a 7ª proteção).
    - `79. Rosa dos Ventos`: não interditar; adicionar aviso de atenção na segurança entre a 1ª e a 2ª proteção.
    - `80. Monte Calvário`: preencher `quantidade_protecoes_intermediarias: 6` e avisar sobre grampos de olhal estreito e parada de difícil visualização da base.
    - `84. Só para elas`: informar compartilhamento temporário da parada com a via *Prestobarba*.
    - `85. Prestobarba`: orientar o uso da parada original no alinhamento da via (desconsiderando a parada extra à direita).
    - `86. Bigode Limpo`: orientar o uso da parada no final da linha original (desconsiderando a parada dupla antiga mais abaixo à esquerda).
    - `92. Meio Cubanos`: não interditar; adicionar aviso de que a via móvel não possui parada (top rope) instalada no topo (`quantidade_protecoes_parada: 0`).
    - `94. Tripla Traição`: recomendar desmontagem por rapel devido ao atrito na aresta e atenção na segurança por risco de queda na aresta (sem menção subjetiva a graduação).
    - `97. Rota de colisão`: lance final mais esticado entre a 4ª proteção e a parada.
    - `99. Vale Perdido`: manter orientação da ponte de pedra e bloco na base, recomendando *stick clip*.
    - `100. Consolo da Surucucu`: linha em diagonal/travessia, recomendando limpar a via escalando de segundo.
    - `103. Jegue Voador`: lance mais esticado entre a 3ª e a 4ª proteção.
- **Atualização do Relatório Consolidado no Google Docs (`1MDqztuc2f4zKHfUeX_xBjNso7Izohre6s53erApKYZY`)**:
  - Atualizar a data de referência para `09/11/2026`, contemplando as manutenções de `05/09/2026` e `12/10/2026` e elevando para 9 o total de vias manutenidas (`76`, `77`, `78`, `82`, `86`, `87`, `88`, `94`, `99`).
  - Atualizar o Painel Geral (Parte I) e as fichas individuais (Parte III) para: `76. Cariocas não dizem Uai`, `78. Aceitam-se Sugestões` (7 intermediárias, Classe 1 Liberada), `79. Rosa dos Ventos` (reclassificada para Classe 2 Atenção), `82. Três dentro, três fora` (1 kit top rope inox + 2 kits PinGo), `86. Bigode Limpo`, `87. Bigode de Cristo` (Classe 1 Liberada), `88. Bigode Sujo` (+1 costura fixa inox), `92. Meio Cubanos` (reclassificada para Classe 2 Atenção — aviso de ausência de top) e `99. Vale Perdido`.
  - Adicionar seção consolidando o Relatório de Estoque e Utilização de Proteções ACEC-MG (item 5.5 do Termo) e o controle separado de doações de Renato Utsch (`09/11/2026`).

## Capabilities

### New Capabilities

<!-- Nenhuma nova capability de software; atualização de dados de croqui e documentação externa. -->

### Modified Capabilities

<!-- Nenhuma alteração de requisito de sistema (`skip_specs: true`). -->

## Impact

- **Dados do Croqui Afetados**:
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/croqui.yaml`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/creditos.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_1.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_3.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_4.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_5.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_7.md`
  - `database/br_mg_lagoa_santa_gruta_da_lapinha/setor_mapa_8.md`
  - `generated/br_mg_lagoa_santa_gruta_da_lapinha/` (após compilação)
- **Documentação Externa Afetada**:
  - Google Docs `1MDqztuc2f4zKHfUeX_xBjNso7Izohre6s53erApKYZY` (*Relatório Consolidado de Inspeções e Manutenções - Gruta da Lapinha*)
