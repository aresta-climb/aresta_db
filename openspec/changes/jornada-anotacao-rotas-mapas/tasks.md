## 1. Testes de Integração em Primeiro Lugar (Princípio V de AGENTS.md)

- [x] 1.1 Criar teste de integração de criação direta de nova rota com paleta "+ Nova Rota", geração de nós (início automático "1", sem TOP desnecessário), criação da entidade no setor e linkagem automática em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.2 Criar teste de integração para variante com bifurcação e fatiamento automático no meio de curva existente, inserção de nó de corte, redistribuição ordenada de IDs e desambiguação de topos ("A" e "B") em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.3 Criar teste de integração para rota convergindo no mesmo topo de via existente com compartilhamento harmônico de nó final e identificador comum em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.4 Criar teste de integração para rota de travessia que compartilha segmento intermediário de via existente (fatiamento em três subpartes contíguas) em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.5 Criar teste de integração para reversão total atômica via Undo (Ctrl+Z) com reconstituição integral da linha original e remoção da escalada criada, seguido de restabelecimento via Redo (Ctrl+Y) em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.6 Criar teste de integração para múltiplos mapas no mesmo setor: persistência do mesmo número identificador em fotos de ângulos distintos e garantia de IDs de POI disjuntos em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.7 Criar teste de integração para sincronização de nós soldados ("sticky"): arrasto de nó compartilhado na cena gráfica atualizando todas as linhas conectadas simultaneamente em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.8 Criar teste de integração para busca de escalada pré-existente sem traçado na paleta, seleção sem duplicação no setor e vinculação de traçado em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.9 Criar teste de integração para cancelamento gracioso (Esc / botão direito) no meio do traçado sem deixar nós órfãos ou lixo na cena e no modelo em `editor/views/jornada_rotas_integracao_test.py`
- [x] 1.10 Criar teste de integração validando o pipeline completo de compilação (`validar_referencias_mapa`) sobre croqui com variantes complexas fatiadas, certificando ausência de POIs órfãos ou referências quebradas em `editor/views/jornada_rotas_integracao_test.py`

## 2. Biblioteca Core de Topologia e Fatiamento (Princípio II - Library-First)

- [x] 2.1 Criar testes unitários para projeção de coordenadas e detecção de snap magnético em nós e segmentos em `editor/core/topologia_trajeto_test.py`
- [x] 2.2 Implementar projeção geométrica e cálculo de snap magnético em `editor/core/topologia_trajeto.py` e verificar aprovação dos testes com 100% de cobertura
- [x] 2.3 Criar testes unitários para algoritmo de fatiamento de traçado (split em nó existente e split com inserção no meio da curva) em `editor/core/topologia_trajeto_test.py`
- [x] 2.4 Implementar fatiamento de traçados e redistribuição de IDs de segmentos em `editor/core/topologia_trajeto.py` e verificar aprovação dos testes com 100% de cobertura
- [x] 2.5 Criar testes unitários para convenção semântica Ouroboulder (início sequencial, saídas compartilhadas "1, 2" e desambiguação de TOP "A, B, C") em `editor/core/topologia_trajeto_test.py`
- [x] 2.6 Criar testes unitários para escopo de setor: reutilização de número de escalada existente, próximo número global do setor e geração de IDs de POI disjuntos em `editor/core/topologia_trajeto_test.py`
- [x] 2.7 Implementar resolução de rótulos semânticos, escopo de setor e geração de IDs disjuntos em `editor/core/topologia_trajeto.py` e verificar aprovação dos testes com 100% de cobertura

## 3. Diálogo de Seleção e Criação Rápida de Rota

- [x] 3.1 Criar testes unitários para `DialogoNovaRotaMapa` em `editor/views/dialogos/dialogo_nova_rota_mapa_test.py` validando busca de escaladas sem traçado e criação inline
- [x] 3.2 Implementar a paleta `DialogoNovaRotaMapa` com busca com autocompletar e opções de tipo/grau em `editor/views/dialogos/dialogo_nova_rota_mapa.py` e verificar aprovação com 100% de cobertura

## 4. Orquestração no Controller com Macro de Histórico (Princípio VII)

- [x] 4.1 Criar testes unitários no `editor/controllers/mapas_controller_test.py` para o método `adicionar_rota_com_tracado` e verificação de atomiciadade no `QUndoStack`
- [x] 4.2 Implementar `adicionar_rota_com_tracado` em `editor/controllers/mapas_controller.py` utilizando `pilha.beginMacro` / `pilha.endMacro` garantindo IDs disjuntos no setor e verificar aprovação com 100% de cobertura

## 5. Integração Gráfica e Remoção do Botão Legado no Editor de Mapas

- [x] 5.1 Criar testes de interface no `editor/views/widget_editor_mapas_test.py` verificando a remoção do botão legado "Nova Linha / Escalada", a presença do botão "+ Nova Rota", atalho `R` e o modo de desenho com snap
- [x] 5.2 Remover o botão legado `btn_add_linha` e os métodos associados de criação desconectada de linha no `editor/views/widget_editor_mapas.py`
- [x] 5.3 Adicionar o botão "+ Nova Rota", atalho `R`, mira visual de snap magnético e conexão ao `MapasController` no `editor/views/widget_editor_mapas.py`
- [x] 5.4 Implementar a sincronização de arrasto de nós soldados ("sticky") para alças coincidentes no `editor/views/widget_editor_mapas.py` e cobrir com testes unitários na view

## 6. Verificação e 100% de Cobertura de Testes (Princípio III de AGENTS.md)

- [x] 6.1 Executar a suíte completa de testes de integração em `editor/views/jornada_rotas_integracao_test.py` e certificar que todos os 10 cenários passam
- [x] 6.2 Executar a suíte completa com medição de cobertura (`pytest --cov=editor`) e certificar que todos os arquivos criados e modificados possuem 100% de unit test coverage
