## Context

O Editor de Mapas combina comandos na pilha global de histórico (`QUndoStack` no `MapasController`), convenções visuais e semânticas de estilo Ouroboulder e uma biblioteca pura de geometria e topologia (`editor/core/topologia_trajeto.py`).

Durante testes e anotações em mapas reais de boulder e vias esportivas (como no setor "Bloco Viva o Climb"), três falhas críticas foram identificadas:
1. Um nó de topo com letra "A" aparecia indevidamente em rotas isoladas, duplicado por trás do traçado e ausente na referência.
2. A criação de múltiplas rotas gerava colisão de IDs de POI (`linha_1`) e números de início (`1`), fundindo a seleção e a representação das linhas na cena.
3. O comando de Desfazer (`Undo`) deixava traçados órfãos visíveis no canvas e destruía POIs pré-existentes (como círculos de início/saída).

A causa-raiz combina:
- Falta de verificação par a par em `desambiguar_topos` (aplicando letras para qualquer mapa com mais de uma rota).
- Falha ao inspecionar o mapa ativo e ao desembrulhar estruturas `ArquivoSetor` na geração de IDs disjuntos e sequenciamento de números.
- Um descompasso de índices no loop de desambiguação de `adicionar_rota_com_tracado`, onde o índice da lista filtrada de linhas (`linhas_atuais`) era usado como índice no array global de `pontos_de_interesse`, sobrescrevendo POIs de outros tipos e corrompendo a pilha do Undo.

## Goals / Non-Goals

**Goals:**
- **Desambiguação par a par sob demanda real**: marcar topos com `FIM_TOP` e letras sequenciais ('A', 'B'...) apenas em convergências reais no mesmo ponto ou bifurcações a partir de tronco/início/nós comuns.
- **Isolamento de rotas autônomas**: rotas sem confluência permanecem com nó final `PASSAGEM` e sem rótulo textual.
- **Restauração de topo após Undo**: ao desfazer ou deletar uma variante, a rota sobrevivente deve ser automaticamente recalculada para nó de `PASSAGEM` isolado.
- **Índice real em `mover_poi`**: mapear de forma exata e confiável o índice de cada linha no array global `pontos_de_interesse` antes de emitir o comando `CmdAlterarRepeatedItem`.
- **Desembrulho robusto de setor e prioridade ao mapa ativo**: garantir que `desembrulhar_setor` suporte `Setor`, `ArquivoSetor` e proxies, e que `gerar_id_poi_disjunto_setor` e `calcular_proximo_numero_inicio_setor` inspecionem prioritariamente o mapa ativo.
- **Integridade visual no Undo**: garantir que a reversão de uma adição remova completamente todos os elementos da nova rota da cena gráfica do Qt sem corromper POIs vizinhos.

**Non-Goals:**
- Não alterar a matemática de interpolação spline Catmull-Rom para curvas Bézier.
- Não alterar o comportamento de vínculo manual de POIs no painel lateral de referências.
- Não alterar formatos de serialização de croquis em disco (Markdown/YAML ou Protobuf).

## Decisions

### 1. Desambiguação de Topos por Análise de Grafo Par a Par
- **Decisão:** Avaliar a relação topológica entre cada par de rotas $(R_i, R_j)$ no mapa:
  - Seja $P_{\text{fim}}(R)$ a coordenada do último nó da rota e $P_{\text{inicio}}(R)$ a do primeiro nó.
  - *Convergência*: Se $\text{dist}(P_{\text{fim}}(R_i), P_{\text{fim}}(R_j)) \le 5.0\text{px}$, ambos os nós finais compartilham a mesma letra de topo e são configurados como `FIM_TOP`.
  - *Bifurcação*: Se $(IDs_i \cap IDs_j \neq \emptyset) \lor (\text{dist}(P_{\text{inicio}}(R_i), P_{\text{inicio}}(R_j)) \le 5.0\text{px}) \lor (\text{nós intermediários coincidentes})$, e $\text{dist}(P_{\text{fim}}(R_i), P_{\text{fim}}(R_j)) > 5.0\text{px}$, cada final recebe uma letra sequencial distinta ('A', 'B'...) e é configurado como `FIM_TOP`.
  - *Isolada*: Se uma rota $R_k$ não apresenta convergência nem bifurcação com nenhuma outra rota do mapa, seu nó final é forçado para `tipo = PASSAGEM` e `rotulo = ""`.
- **Alternativa Rejeitada:** Checar apenas a contagem total de rotas (`len(rotas) > 1`), pois causava rotulação de topo espúria em vias que não tinham relação alguma entre si no mesmo bloco de rocha.

### 2. Resolução do Índice Real de POIs no `MapasController`
- **Decisão:** Substituir a indexação pelo `enumerate` da lista filtrada por uma busca do índice real no array `pontos_de_interesse`:
  ```python
  for l_original, l_modificada in zip(linhas_atuais, linhas_copia):
      if l_original != l_modificada:
          idx_real = list(msg_mapa_proxy.pontos_de_interesse).index(l_original)
          self.mover_poi(msg_mapa_proxy, idx_real, l_original, l_modificada)
  ```
- **Racional:** Quando o mapa possui círculos, retângulos ou polígonos intercalados com linhas, o índice relativo em `linhas_atuais` não coincide com o índice absoluto em `pontos_de_interesse`. Usar `idx_real` elimina a sobrescrita acidental de outros POIs e assegura que o `CmdAlterarRepeatedItem` registre o objeto correto no histórico para o `Undo`.

### 3. Desembrulho de Setor e Inspeção Prioritária do Mapa Ativo
- **Decisão:**
  - Criar `desembrulhar_setor(setor_msg)` em `topologia_trajeto.py`. Se o objeto contiver `.conteudo`, acessa `.conteudo`. Se for proxy `ReadOnlyProxy`, acessa `_obj`.
  - Atualizar `gerar_id_poi_disjunto_setor` e `calcular_proximo_numero_inicio_setor` para receber o `mapa_ativo` como parâmetro (ou incluir seus elementos nos conjuntos de busca). Mesmo que o setor fornecido seja `None` ou pertença a outra hierarquia, os elementos do mapa ativo são inspecionados em primeiro lugar.
  - Em `finalizar_modo_nova_rota` do `WidgetEditorMapas`, garantir que o setor passado para `adicionar_rota_com_tracado` seja sempre o setor resolvido a partir do mapa ativo (`self._obter_setor_atual()`), e não um `setor_obj` estrangeiro retornado de busca global.

### 4. Ciclo de Vida Visual e Integridade da Cena no Qt
- **Decisão:**
  - Com IDs estritamente únicos (`linha_1`, `linha_2`, `linha_3`), o dicionário `self.itens_poi` no `WidgetEditorMapas` mapeia de forma limpa cada elemento da cena.
  - Ao executar `Undo`, o comando `CmdAdicionarRepeated` remove o POI correto da lista e a View remove o respectivo `QGraphicsItem` da cena. Como nenhum outro POI foi sobrescrito por descompasso de índice, o estado visual é 100% restaurado sem deixar traços ou nós zumbis.

## Risks / Trade-offs

- **[Tolerância de proximidade em topos]** → Rotas podem convergir visualmente com diferença de 1 ou 2 pixels decorrente de cliques manuais. *Mitigação*: Usar coordenadas inteiras arredondadas e tolerância de proximidade ($\le 5.0\text{px}$) para detecção de topos e nós coincidentes.
- **[Reversão de topos após exclusão de variante]** → Ao remover uma variante, a rota sobrevivente precisa voltar a ser isolada. *Mitigação*: Como a desambiguação analisa par a par e faz parte do macro atômico de Undo/Redo do controller, ao desfazer uma adição de variante, a mutação da rota original é revertida automaticamente pela pilha de histórico.
