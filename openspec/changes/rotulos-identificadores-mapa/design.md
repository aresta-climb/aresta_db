## Context

Consulte `proposal.md` para motivação e `specs/` para os requisitos normativos.

Atualmente, `Mapa_Referencia` armazena uma lista de strings `ids`. Quando a referência aponta para nós de traçados vetoriais suaves (`LinhaTrajeto`), os nós (`NoTrajeto` em `conteudo.nos` ou `MarcadorCompilado` em `compilado.marcadores`) armazenam semanticamente os círculos identificadores da escalada (`CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO`, `FIM_TOP`) acompanhados de seu campo `rotulo`.

No frontend (`aresta_app`), `getLabelsForRef` em `mapa_interativo.dart` e `_resolveRouteMapData` em `setor_functions.dart` duplicam uma lógica que falha ao inspecionar nós de linhas vetoriais e recorre a `labels.add(id)`, expondo IDs internos de banco de dados aos usuários.

No backend/ferramental (`aresta_db`), o editor carece de visualização imediata do codenome no `CardReferencia` e o compilador não alerta sobre referências sem identificadores.

## Goals / Non-Goals

**Goals:**
- Centralizar a extração de codenomes no `aresta_app` em uma função pura e testável (`extrairRotuloReferencia`).
- Eliminar qualquer vazamento de IDs técnicos (`linha_XX`) na interface móvel.
- Inserir validação no compilador do `aresta_db` alertando autores sobre referências sem rótulos ou círculos identificadores.
- Enriquecer o `CardReferencia` do editor com preview de codenome e botão para inverter a ordem de IDs de forma reversível (Undo/Redo).
- Manter 100% de cobertura de testes em ambas as bases (Dart e Python).

**Non-Goals:**
- Modificar o schema `.proto` do croqui (nenhuma migração de dados ou recompilação de Protobuf necessária).
- Reordenação mágica heurística de nós no app (a ordem dos IDs e nós definida pelo autor é estritamente soberana).

## Decisions

### Decisão 1: Ordem natural estrita de encontro dos identificadores
- **Escolha**: Iterar sobre `ref.ids` na ordem exata da lista e, para cada linha, iterar por seus nós de início a fim. Coletar os valores de `rotulo` para nós do tipo `CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO` ou `FIM_TOP`. Para POIs tradicionais que não são linhas, coletar `p.label`.
- **Alternativa considerada**: Separar artificialmente em buckets de "Início" e "Fim". Rejeitada porque vias e travessias podem possuir múltiplos pontos de controle e variantes que não se reduzem a apenas 1 início e 1 fim.

### Decisão 2: Deduplicação de nós idênticos consecutivos
- **Escolha**: Se dois segmentos contíguos se conectam em um nó comum compartilhado que possui o mesmo rótulo (ex: `['5', '5', 'C']`), comprime-se para `['5', 'C']`.
- **Alternativa considerada**: Deduplicação global via `Set`. Rejeitada porque uma via em laço ou travessia pode legitimamente passar pelo mesmo ponto mais de uma vez ou possuir variações com identificadores repetidos intencionalmente em pontos distintos.

### Decisão 3: Warning não-bloqueante no deploy do `aresta_db`
- **Escolha**: Integrar a checagem na rotina `validar_referencias_mapa()` de `scripts/preparar_submissao_lib.py`, que já executa durante o deploy de croquis. O aviso utiliza a frase exata:
  *"A referência '{nome}' no Mapa {idx} em {contexto} não possui label ou rótulo em círculo identificador e não exibirá identificador no mapa do aplicativo."*
- **Alternativa considerada**: Bloquear o build com erro fatal (`sys.exit(1)`). Rejeitada porque causaria quebra em croquis legados em produção que ainda precisam de revisão dos autores.

### Decisão 4: Inversão de IDs no Editor integrada com `QUndoCommand`
- **Escolha**: Adicionar botão `[ 🔄 Inverter ]` ao lado do indicador de IDs no `CardReferencia`. Ao ser acionado, chama `mapas_controller.alterar_referencia()` passando uma cópia profunda da referência com `ids.reverse()`.
- **Alternativa considerada**: Mutação direta no callback de clique do botão. Rejeitada por violar frontalmente o Princípio VII de Engenharia Aresta (toda alteração na GUI deve ser reversível na pilha de Undo/Redo).

## Risks / Trade-offs

- **[Risco: Croquis legados com referências sem label]** → *Mitigação*: O validador do compilador emitirá avisos visíveis no log do deploy detalhando exatamente qual via/mapa está afetada, permitindo correção proativa pelos autores no editor.
- **[Risco: Inversão de linha única com múltiplos nós internos]** → *Mitigação*: Se uma única linha vetorial contiver nós em ordem invertida (ex: desenhada do topo para a base), a inversão dos IDs da referência não inverte os nós internos da linha. Nesses casos, o autor pode usar as ferramentas já existentes de edição de linha no editor ou inverter os nós do trajeto.
