## Why

Ao adicionar e manipular rotas de escalada no Editor de Mapas, ocorrem falhas graves na integridade topológica, na resolução de identificadores e na pilha de histórico (Undo/Redo), gerando três sintomas críticos relatados pelos usuários:

1. **Topo "A" fantasma por trás do traçado e divergente do painel (Problema 1)**:
   - A rotina `desambiguar_topos` aplicava letras de topo sequenciais ("A", "B"...) de forma cega sempre que existisse mais de uma rota no mapa (`len(rotas) > 1`), mesmo quando as vias eram 100% isoladas (em pedras opostas, sem início, tronco ou topo compartilhados).
   - Além disso, um descompasso de índices no método `adicionar_rota_com_tracado` do `MapasController` utilizava o índice da lista filtrada de linhas (`linhas_atuais`) para chamar `mover_poi`, sobrescrevendo indevidamente POIs não-linha (como círculos de saída `sai1`) por uma duplicata da linha na cena gráfica, criando o efeito visual de um círculo "A" avulso renderizado por trás do traçado original, enquanto a referência exibia apenas `[ 1 ]`.

2. **Rotas novas fundidas com o mesmo identificador (`linha_1`) e mesmo início (`1`) (Problema 2)**:
   - As rotinas de geração de ID (`gerar_id_poi_disjunto_setor`) e cálculo de início (`calcular_proximo_numero_inicio_setor`) falhavam ao inspecionar o setor quando envelopado em `ArquivoSetor` (onde os mapas residem em `conteudo.mapas`) ou através de proxies, e omitiam a inspeção prioritária do mapa ativo (`msg_mapa_proxy`).
   - Com o conjunto de IDs existentes avaliado como vazio, tanto a segunda quanto a terceira rota recebiam `id = "linha_1"` e início `"1"`. Como ambas as referências apontavam para `linha_1`, selecionar uma rota destacava a outra simultaneamente em ciano.

3. **Falha de reversão no Undo com traçado órfão remanescente na tela (Problema 3)**:
   - O descompasso de índices fazia o `mover_poi` substituir o POI do índice 1 pela linha recém-criada, enquanto `adicionar_linha` inseria a linha no índice final (ex: índice 3).
   - Ao disparar Desfazer (Undo), a adição no índice 3 era revertida, mas a alteração no índice 1 desfazia restaurando a linha registrada como estado anterior, deixando uma linha zumbi permanente no canvas do editor e destruindo o POI original.

Esta mudança corrige a desambiguação de topos para atuar estritamente sob demanda topológica real, garante o desembrulho seguro de setores com prioridade absoluta para o mapa ativo, e corrige o mapeamento de índices reais de POIs no `MapasController`, restaurando a integridade da topologia e da pilha atômica de Undo/Redo.

## What Changes

- **Desambiguação seletiva de topos sob demanda topológica**:
  - Refatora `desambiguar_topos` em `editor/core/topologia_trajeto.py` para comparar rotas par a par.
  - Atribui círculos identificadores de final (`FIM_TOP` com letras 'A', 'B'...) exclusivamente em casos de:
    - *Convergência real* no mesmo ponto de topo ($\le 5\text{px}$).
    - *Bifurcação* a partir de tronco/início compartilhado para topos distintos ($> 5\text{px}$).
  - Rotas isoladas sem nenhuma confluência permanecem com o nó final como `PASSAGEM` e sem rótulo textual (`""`).
  - Garante que a exclusão ou reversão de uma variante restaure a rota sobrevivente para o estado de rota isolada.

- **Correção do índice real de POIs no `MapasController`**:
  - Modifica `adicionar_rota_com_tracado` em `editor/controllers/mapas_controller.py` para localizar o índice real de cada linha em `msg_mapa_proxy.pontos_de_interesse` via `list(msg_mapa_proxy.pontos_de_interesse).index(l_original)`.
  - Impede a sobrescrita acidental de POIs não-linha (círculos, retângulos, polígonos) e elimina a duplicação espúria de itens na cena gráfica.

- **Desembrulho robusto de setor e prioridade ao mapa ativo**:
  - Implementa a função pura `desembrulhar_setor` em `editor/core/topologia_trajeto.py` para extrair seguramente mapas e escaladas de `Setor`, `ArquivoSetor` (`conteudo`), proxies ou estruturas aninhadas.
  - Atualiza `gerar_id_poi_disjunto_setor` e `calcular_proximo_numero_inicio_setor` para inspecionar prioritariamente os POIs do mapa ativo (`msg_mapa_proxy`), prevenindo qualquer colisão de identificador (`linha_1`, `linha_2`...) ou reutilização indevida de números de início (`1`, `2`...).
  - Ajusta `finalizar_modo_nova_rota` em `editor/views/widget_editor_mapas.py` para garantir que o setor associado ao traçado seja sempre o setor do mapa ativo editado (`_obter_setor_atual()`).

- **Integridade da cena gráfica no Undo/Redo**:
  - Com índices reais e identificadores estritamente disjuntos, a reversão via histórico (`QUndoStack`) remove completamente todos os itens visuais da nova rota da `QGraphicsScene` sem deixar elementos gráficos órfãos.

## Capabilities

### Modified Capabilities
- `editor-mapas`: Atualiza os requisitos de topologia de rotas para desambiguação sob demanda real de topos, garantia estrita de identificadores disjuntos entre traçados e reversibilidade completa de adições via histórico.

## Impact

- **Código Afetado**:
  - `editor/core/topologia_trajeto.py`: `desambiguar_topos`, `desembrulhar_setor`, `gerar_id_poi_disjunto_setor`, `calcular_proximo_numero_inicio_setor`.
  - `editor/controllers/mapas_controller.py`: `adicionar_rota_com_tracado`.
  - `editor/views/widget_editor_mapas.py`: `finalizar_modo_nova_rota`.
- **Testes**:
  - `editor/core/topologia_trajeto_test.py`: testes unitários de desambiguação seletiva, desembrulho de setor e unicidade de IDs com mapa ativo.
  - `editor/controllers/mapas_controller_test.py`: testes de adição de rotas em mapas com POIs mistos e reversibilidade atômica no Undo.
  - `editor/views/widget_editor_mapas_test.py`: testes de interação visual, ausência de seleção compartilhada e limpeza completa da cena gráfica.
