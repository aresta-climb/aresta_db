## Context

Ver `proposal.md` para motivação e antecedentes do problema. O sistema atual possui `WidgetEditorMapas` com visualizador `QGraphicsView` e itens gráficos derivados de `BaseItemPOI` (`ItemTrajetoLinha`, `AlcaNoTrajeto`). As mutações de estado ocorrem através do `MapasController` despachando comandos na pilha `QUndoStack`. O modelo de dados Protobuf (`croqui.proto`) já suporta uma lista ordenada de strings em `referencias.ids` e uma lista de `NoTrajeto` em `LinhaTrajeto.conteudo.nos`.

Para lidar com a alta complexidade inerente à geometria de curvas Bézier, projeções de snap, fatiamento topológico de grafos e sincronização de nós, o design segue rigorosamente os Princípios de Engenharia Aresta (`AGENTS.md`), priorizando uma biblioteca desacoplada da interface (`editor/core/topologia_trajeto.py`) com 100% de cobertura de testes unitários e testes de integração de contratos antes da amarração dos componentes na interface gráfica.

## Goals / Non-Goals

**Goals:**
- Prover um diálogo/paleta ágil (`DialogoNovaRotaMapa`) que permite tanto selecionar uma escalada pré-existente sem traçado no setor quanto criar uma nova escalada (nome, tipo, grau) com foco imediato no teclado.
- Remover o botão legado `btn_add_linha` ("Nova Linha / Escalada") e seus fluxos manuais de popup desconectado de entidades.
- Implementar modo interativo de desenho ponto a ponto com snap magnético visual e geométrico em nós e corpos de linhas existentes.
- Prover fatiamento automático de traçados ("sticky") em vértices existentes ou em qualquer ponto do meio de uma curva (com projeção e inserção de nó de corte).
- Aplicar a convenção semântica Ouroboulder: inícios numerados sequencialmente (`1`, `2`, `3`...), saídas compartilhadas rotuladas em conjunto (`1, 2`), topos desambiguados com letras (`A`, `B`, `C`...) e nós intermediários com símbolos geométricos.
- Garantir coerência e unicidade de identificação no escopo unificado de todo o Setor: se a mesma escalada já possuir traçado/número em outra foto/mapa do setor, reutilizar o mesmo número; calcular o próximo número disponível considerando todos os mapas do setor; e garantir que todos os IDs de POI gerados sejam mutuamente disjuntos entre fotos do setor.
- Implementar regra de desambiguação sob demanda para TOPs: não poluir rotas isoladas com círculos de TOP; gerar círculos identificadores com letras de TOP apenas quando duas ou mais rotas terminarem em topos distintos ou convergirem no mesmo final.
- Garantir reversibilidade atômica de todas as operações (criação de entidade, fatiamento, novas linhas e atualização de referências) através de macros `QUndoCommand` no histórico.
- Sincronizar nós de junção compartilhados ("sticky") durante operações subsequentes de arrasto/edição.
- Atingir 100% de cobertura de testes unitários (Princípio III) e aderir a TDD (Princípio IV) e Library-First (Princípio II).

**Non-Goals:**
- Não alterar o schema Protobuf (`croqui.proto`), mantendo total compatibilidade retroativa com os croquis existentes e compiladores.
- Não remover as ferramentas manuais para geometrias não-lineares (círculos, caixas e polígonos), preservando o caso de uso de digitalização de croquis em PDF.
- Não introduzir dependências externas pesadas ou heurísticas de inteligência artificial / visão computacional para traçado de linhas.

## Decisions

### Decisão 1: Arquitetura Library-First em `editor/core/topologia_trajeto.py` (Princípio II)
- **Escolha**: Toda a lógica matemática de projeção na spline Catmull-Rom, cálculo de snap magnético, fatiamento de nós em sub-linhas, distribuição de IDs e determinação semântica de inícios/saídas/tops reside em um módulo Python puro em `editor/core/topologia_trajeto.py`.
- **Racional**: Não misturar regras de cálculo geométrico e topologia na camada de visualização Qt (`WidgetEditorMapas`). Esse módulo opera sobre dicionários de nós e primitivas matemáticas puras, permitindo testes unitários rápidos, profundos e sem mock de interface.
- **Alternativas consideradas**:
  - *Embutir a lógica diretamente no `WidgetEditorMapas`*: Descartado por violar o Princípio II (`Library-First`) e tornar a cobertura de testes 100% frágil e dependente de emulação de eventos Qt.

### Decisão 2: Substituição Definitiva do Botão "Nova Linha / Escalada"
- **Escolha**: O botão `btn_add_linha` e os métodos `iniciar_modo_desenho_linha`, `adicionar_ponto_desenho_linha`, `finalizar_modo_desenho_linha` são removidos e substituídos integralmente pelo fluxo `btn_nova_rota` com atalho `R`.
- **Racional**: Elimina código duplicado e evita que o usuário crie linhas "órfãs" que geram avisos de compilação por não estarem linkadas a nenhuma referência de escalada.

### Decisão 3: Paleta Unificada de Busca com Criação Inline (`DialogoNovaRotaMapa`)
- **Escolha**: Uma janela modal enxuta contendo campo de busca com autocompletar das escaladas do setor atual que não possuem traçado no mapa ativo, além de opção automática `(+) Criar Nova Escalada: "<nome>"` com seleção de tipo e grau.
- **Racional**: Fluxo contínuo sem troca de contexto; atende quem já cadastrou os dados antes no Editor de Dados e quem está criando rotas na rocha do zero.

### Decisão 4: Fatiamento Topológico Ponto a Ponto e Inserção no Meio
- **Escolha**: Quando a nova rota conecta a uma linha existente:
  - Se coincidir com nó existente: usa o nó existente como ponto de fatiamento.
  - Se clicar no meio de uma curva entre dois nós: projeta o clique na spline Catmull-Rom, insere um nó novo de corte e fatia a linha original em duas subpartes contíguas.
- **Racional**: Garante continuidade matemática e visual exata sem gerar sobreposições ou quebras bruscas de curvatura.

### Decisão 5: Regra de TOP Sob Demanda para Desambiguação
- **Escolha**: Rotas isoladas terminam com nó de tipo `PASSAGEM` ou término natural sem círculo de TOP. Quando uma nova rota se conecta a uma linha existente e bifurca para outro topo, o editor atualiza retroativamente o topo da rota original para `FIM_TOP` ("A") e o da nova rota para `FIM_TOP` ("B"). Se convergirem no mesmo topo, ambas compartilham o nó com letra única.
- **Racional**: Reduz ruído visual na foto da pedra e segue o padrão Ouroboulder.

### Decisão 6: Resolução de Rótulos e IDs no Escopo do Setor
- **Escolha**: A biblioteca `topologia_trajeto.py` implementa funções puras que inspecionam o conjunto completo de mapas do setor (`setor.mapas`):
  1. `obter_rotulo_escalada_no_setor(setor, nome_escalada)`: Se a escalada já tiver número de início em outro mapa do mesmo setor, reutiliza o mesmo número.
  2. `calcular_proximo_numero_inicio_setor(setor)`: Analisa todos os nós de início em todos os mapas do setor e sugere `max(numeros_usados) + 1`.
  3. `gerar_id_poi_disjunto_setor(setor, prefixo)`: Coleta o conjunto unificado de todos os IDs de POI de todos os mapas do setor e gera um ID estritamente disjunto com sufixo determinístico, prevenindo colisões inter-mapas.
- **Racional**: Mantém a verdade única do setor: a mesma rota tem o mesmo número em qualquer foto do mesmo bloco, e nenhum ID colide ao compilar o setor.

### Decisão 7: Macro Atômico de Undo/Redo no Histórico (Princípio VII)
- **Escolha**: O método `MapasController.adicionar_rota_com_tracado(...)` abre um macro com `pilha.beginMacro(...)`, executa a criação da escalada no setor (se for nova), as mutações de fatiamento de linhas e criação de referências, e fecha com `pilha.endMacro(...)`.
- **Racional**: Um único toque em `Ctrl+Z` reverte 100% da operação, restaurando a linha original íntegra e removendo a escalada criada sem estados inconsistentes intermediários.

## Estrutura do Código (Library-First & MVC)

```
editor/
├── core/
│   ├── topologia_trajeto.py       # [NOVO] Funções puras: snap, projeção, fatiamento, escopo de setor, rótulos
│   └── topologia_trajeto_test.py  # [NOVO] Testes unitários com 100% de cobertura
├── controllers/
│   ├── mapas_controller.py        # [MODIFICADO] adicionar_rota_com_tracado com macro atômico
│   └── mapas_controller_test.py   # [MODIFICADO] Testes de comandos de histórico e reversão
├── views/
│   ├── dialogos/
│   │   ├── dialogo_nova_rota_mapa.py      # [NOVO] Paleta rápida de busca e criação inline
│   │   └── dialogo_nova_rota_mapa_test.py # [NOVO] Testes unitários do diálogo
│   ├── widget_editor_mapas.py             # [MODIFICADO] Botão + Nova Rota (R), remoção btn legado
│   ├── widget_editor_mapas_test.py        # [MODIFICADO] Testes da interface e nós soldados
│   └── jornada_rotas_integracao_test.py   # [NOVO] Teste de integração end-to-end (Princípio V)
```

## Especificação Detalhada dos 10 Testes de Integração (`jornada_rotas_integracao_test.py`)

Cada teste de integração em `editor/views/jornada_rotas_integracao_test.py` possui docstrings completas e verifica um contrato essencial do sistema:

1. **`test_01_criacao_direta_nova_rota`**:
   - *O que testa*: Fluxo de ponta a ponta de criação de uma nova via isolada na rocha a partir de foto limpa.
   - *Ação*: Aciona `+ Nova Rota`, preenche nome ("Via Central"), tipo (Boulder) e grau (V4) na paleta. Desenha 4 nós na cena e conclui com duplo clique.
   - *Checagens*:
     - `setor.escaladas` contém a nova entidade "Via Central".
     - `mapa.pontos_de_interesse` contém exatamente 1 nova linha com ID determinístico.
     - O nó inicial possui `CIRCULO_IDENTIFICADOR` com rótulo "1".
     - O nó final NÃO possui círculo identificador (rota isolada limpa).
     - `mapa.referencias` possui 1 referência com `escalada: "Via Central"` e `ids` apontando para a linha criada.
     - O botão legado `btn_add_linha` não está visível na interface.

2. **`test_02_variante_fatiamento_meio_curva_e_desambiguacao_top`**:
   - *O que testa*: Criação de variante que compartilha início e bifurca no meio de uma curva existente com fatiamento dinâmico.
   - *Ação*: Com a "Via Central" já desenhada, inicia "Variante Direita" (V6). Dá snap no nó inicial (1), snap em nó intermediário, e clica no ponto médio entre nós. Bifurca para a direita e conclui.
   - *Checagens*:
     - O nó de início compartilhado atualiza seu rótulo para "1, 2".
     - A linha original é removida e substituída por 2 sub-linhas (`seg_comum` e `seg_via_central`).
     - A nova linha exclusiva da variante (`seg_variante_direita`) é criada.
     - A referência da "Via Central" é atualizada para conter `[seg_comum, seg_via_central]`.
     - A referência da "Variante Direita" contém `[seg_comum, seg_variante_direita]`.
     - Desambiguação de TOP: o topo da Via Central ganha retroativamente círculo "A" e a Variante ganha círculo "B".
     - A compilação `validar_referencias_mapa` valida sem erros ou órfãos.

3. **`test_03_convergencia_mesmo_top_compartilhado`**:
   - *O que testa*: Rota independente que sobe e converge no mesmo topo de uma via já existente.
   - *Ação*: Inicia terceira rota ("Entrada Esquerda"), clica em pontos livres e no nó final da Via Central.
   - *Checagens*:
     - O nó de início ganha o próximo número "3".
     - O nó final é compartilhado com as coordenadas exatas do topo da Via Central.
     - Ambas as referências referenciam o mesmo topo "A" sem gerar nós ou letras duplicadas.

4. **`test_04_travessia_fatiamento_triplo_intermediario`**:
   - *O que testa*: Rota de travessia que entra no meio de uma linha existente, compartilha nós intermediários e sai para o outro lado.
   - *Ação*: Desenha linha que cruza e acompanha 2 nós de uma linha hospedeira.
   - *Checagens*:
     - A linha hospedeira é dividida em 3 partes (`inicio`, `meio_comum`, `fim`).
     - A referência hospedeira recebe os 3 segmentos em ordem estrita.
     - A referência da travessia recebe `[entrada_propria, meio_comum, saida_propria]`.

5. **`test_05_reversao_total_undo_redo_atomico`**:
   - *O que testa*: Integridade atômica do histórico (Princípio VII).
   - *Ação*: Executa o teste 02 (variante com fatiamento e desambiguação). Em seguida, aciona `undo()` na pilha `QUndoStack`.
   - *Checagens no Undo*:
     - A escalada "Variante Direita" desaparece de `setor.escaladas`.
     - A referência da variante é removida de `mapa.referencias`.
     - As sub-linhas são deletadas e a linha original da "Via Central" é 100% restaurada íntegra.
     - O marcador "A" do topo é removido e o início volta a ser apenas "1".
   - *Checagens no Redo*:
     - Ao acionar `redo()`, todo o estado fatiado, referências e marcadores são restabelecidos com exatidão matemática.

6. **`test_06_multiplos_mapas_setor_consistencia_e_ids_disjuntos`**:
   - *O que testa*: Coerência inter-mapas dentro do mesmo setor.
   - *Ação*: Setor com Mapa 1 (frontal) e Mapa 2 (lateral). Traça "Via Central" no Mapa 1 (recebe "1"). Alterna para o Mapa 2 e traça a mesma "Via Central" na foto lateral. Em seguida, cria uma via nova ("Via do Teto") no Mapa 2.
   - *Checagens*:
     - No Mapa 2, o nó inicial da "Via Central" reutiliza automaticamente o número "1".
     - Todos os IDs de POIs do Mapa 2 são estritamente disjuntos dos IDs do Mapa 1.
     - A "Via do Teto" recebe o próximo número global do setor ("2").

7. **`test_07_sincronizacao_arrasto_nos_soldados_sticky`**:
   - *O que testa*: Comportamento "sticky" de nós compartilhados na cena gráfica.
   - *Ação*: Identifica uma alça `AlcaNoTrajeto` em um nó de bifurcação compartilhado por 2 linhas. Simula evento de arrasto do mouse para nova posição $(x+40, y+20)$.
   - *Checagens*:
     - Todas as linhas que convergem naquele ponto atualizam suas coordenadas simultaneamente na cena.
     - O modelo Protobuf subjacente é atualizado de forma sincronizada.
     - Ao dar `undo()`, todas as linhas retornam à coordenada anterior juntas.

8. **`test_08_busca_escalada_preexistente_sem_duplicacao`**:
   - *O que testa*: Vinculação de linha a uma rota pré-cadastrada no Editor de Dados sem gerar duplicatas.
   - *Ação*: Setor já possui 3 escaladas no modelo. Abre a paleta "+ Nova Rota", filtra pelo nome de uma delas e seleciona. Desenha o traçado.
   - *Checagens*:
     - Nenhuma nova escalada é adicionada em `setor.escaladas` (mantém 3).
     - A linha e a referência são criadas e vinculadas à entidade correta.

9. **`test_09_cancelamento_gracioso_sem_efeitos_colaterais`**:
   - *O que testa*: Cancelamento seguro pelo usuário antes de concluir o desenho.
   - *Ação*: Abre a paleta, digita nova rota, clica 2 nós na cena e pressiona `Esc`.
   - *Checagens*:
     - A cena é limpa de itens temporários.
     - Nenhuma escalada é salva em `setor.escaladas`.
     - Nenhum comando é empilhado na pilha de histórico.

10. **`test_10_validacao_compilacao_croqui_sem_erros`**:
    - *O que testa*: Conformidade final do croqui com as regras do compilador (`preparar_submissao_lib.py`).
    - *Ação*: Executa `validar_referencias_mapa(croqui)` e `calcular_spline_catmull_rom` após a criação de uma rede de rotas e variantes.
    - *Checagens*:
      - Lista de erros retornada por `validar_referencias_mapa` é vazia (`len(erros) == 0`).
      - Nenhum POI do tipo linha é reportado como órfão.
      - Todos os caminhos SVG compilados são gerados com sucesso.

## Risks / Trade-offs

- **[Deformação visual de spline em segmentos fatiados curtos]** → *Mitigação*: Na renderização e compilação de referências com múltiplos segmentos contíguos, a biblioteca `spline_catmull_rom.py` concatena a cadeia de nós antes de gerar o caminho Bézier, garantindo derivadas contínuas ($C^1$) no ponto de junção.
- **[Conflito de IDs de POI entre fotos do setor]** → *Mitigação*: Algoritmo `gerar_id_poi_disjunto_setor` valida a unicidade global em relação à união de todos os mapas do setor antes de emitir qualquer ID.
- **[Complexidade na sincronização de nós soldados]** → *Mitigação*: Quando uma `AlcaNoTrajeto` é movida na cena gráfica, o `WidgetEditorMapas` atualiza todas as alças coincidentes registradas no índice topológico da cena dentro do mesmo ciclo de eventos de mouse.
