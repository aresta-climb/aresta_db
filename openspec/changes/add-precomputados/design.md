## Context

Precisamos evitar que o frontend do aplicativo Aresta (e outras ferramentas que consumam o `.binarypb` gerado) precise varrer todos os picos, grupos, setores e escaladas para descobrir informações simples como: "Quantas vias tem nesse croqui?" ou "Quantos setores existem nesse pico?". O processamento do croqui gera essas árvores e podemos pré-computar esses dados injetando-os nos respectivos protobufs.

## Goals / Non-Goals

**Goals:**
- Injetar pré-computados (totais de escalada, setores e grupos) nos nodes de `Setor`, `Grupo` e `Pico` do `croqui.proto`.
- Injetar precomputados (totais de escalada, setores e grupos) no `ResumoCroqui` do `indice.proto` para acesso rápido antes de baixar o croqui completo.
- Desacoplar a lógica de contagem na rotina de compilação.

**Non-Goals:**
- Contagens detalhadas divididas por modalidade (vias esportivas vs boulders, etc). Por enquanto manteremos apenas o `total_escaladas`.
- Renderização visual desses campos no editor web do banco de dados (`(aresta.mensagem_formato_na_ui) = INVISIVEL`).

## Decisions

- **Múltiplos passes desacoplados (Bottom-up)**: Ao invés de uma travessia genérica enorme que acumula dados em tempo de execução, faremos três passes distintos no Python (`computar_precomputados_setor`, `computar_precomputados_grupo`, `computar_precomputados_pico`). Isso deixa o código modular, testável e legível. 
- **Contagem por length de array**: Para simplificar e atender a demanda atual, contaremos apenas o número de itens inseridos na lista `escaladas` de cada setor. Uma via de múltiplas enfiadas conta como 1 escalada, sem contar suas partições internas.
- **Valores zerados no PB3**: Se não houver setores ou vias, o protocolo (proto3) não envia os dados (omite campos setados para 0). A aplicação que ler precisa prever valores padrão (0).

## Risks / Trade-offs

- **Risk**: Pode haver descasamento no frontend antigo que não sabe ler esses campos (nenhum risco real, a serialização JSON e Protobuf simplesmente ignora campos extras). -> Mitigação: adicionar no final do schema proto e marcar como invisíveis no UI do DB para não bugar o editor.
- **Risk**: Processamento extra na submissão de um croqui. -> Mitigação: iterar as listas é extremamente performático (tempo quase nulo em Python para o tamanho dos nossos croquis) comparado à geração de imagens.
