## Context

O app precisa exibir estatísticas detalhadas sobre os tipos de escaladas (como a quantidade de vias esportivas, móveis, boulders, etc.) para os Picos, Grupos e para o Croqui em geral. Atualmente, os pré-computados recém-adicionados contam apenas os totais absolutos. Realizar a contagem detalhada em runtime no cliente exigiria ler e iterar sobre todos os nós de setores e suas escaladas de forma assíncrona, algo ineficiente. A solução arquitetural é pré-computar esses dados em tempo de compilação e salvá-los nas mensagens do Protobuf.

## Goals / Non-Goals

**Goals:**
- Estender as sub-mensagens de pré-computados com os contadores para cada tipo específico de escalada (`via_esportiva`, `tradicional`, `boulder`, `via_multiplas_enfiadas`, `highline`).
- Adotar o comportamento padrão do Proto3 onde valores iguais a 0 são ocultados, minimizando o impacto no tamanho final dos arquivos YAML e Binários.
- Implementar a contagem desde a base da árvore (Setor) para realizar _roll-ups_ diretos (O(1) após o nó folha) nas camadas superiores (Grupo, Pico, Resumo).

**Non-Goals:**
- Não faremos a quebra detalhada do que existe "dentro" de uma via de múltiplas enfiadas (ex: se é de proteção fixa ou móvel). Ela apenas receberá +1 na categoria "Múltiplas Enfiadas".
- Não usaremos campos do tipo `optional` para contornar o 0. O valor zero deve significar ausência para enxugamento de payload.

## Decisions

- **Nomenclatura dos Campos**: 
  - `total_esportivas` (representando `via_esportiva`)
  - `total_moveis` (representando a variante `tradicional` do modelo)
  - `total_boulders` (representando `boulder`)
  - `total_multiplas_enfiadas` (representando `via_multiplas_enfiadas`)
  - `total_highlines` (representando `highline`)
- **Algoritmo Base (Roll-Up)**:
  - No `preparar_submissao_lib.py`, a função `computar_precomputados_setor` iterará em `escaladas` detectando qual chave do `oneof` existe, e incrementará a estatística no dicicionário `precomputados` do Setor.
  - O `Grupo` e `Pico` apenas agregarão os campos `total_*` resultantes dos filhos (somatória de dicionários simples).
  - Em `deploy_generated.py`, ao gerar o Índice, o mesmo agregador será usado somando os dados já prontos do Pico.

## Risks / Trade-offs

- **[Risco] Compatibilidade com base de dados anterior**: Alterar Protobufs pode quebrar clientes antigos? 
  → **Mitigação**: Não. Os novos campos são estritamente adições e, por estarem nulos por padrão ou omitidos, clientes antigos do app os ignorarão sem falhas de parse.
- **[Trade-off] Redundância Mínima de Dados**: Os totais por tipo acabam refletindo a somatória do `total_escaladas`. Contudo, resolvemos manter o `total_escaladas` no dicionário para facilitar cálculos diretos onde a quebra por tipo não importa.
