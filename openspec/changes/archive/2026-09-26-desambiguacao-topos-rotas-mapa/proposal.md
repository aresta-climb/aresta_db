## Why

No editor de mapas (`aresta_db`), ao adicionar mais de uma rota em um mapa, a função de topologia `desambiguar_topos` converte indevidamente o nó final de **todas** as rotas em círculos identificadores de final (`FIM_TOP`) com letras sequenciais (`A`, `B`, `C`...), mesmo que as rotas sejam totalmente isoladas e independentes (sem início, final, nós ou segmentos compartilhados).

Isso causa poluição visual desnecessária na foto da rocha e rótulos enganosos no aplicativo móvel (`aresta_app`) — por exemplo, exibindo `1-A`, `2-B`, `3-C` para três vias paralelas simples, quando o correto e natural para o escalador é exibir apenas os números de início `1`, `2` e `3`. O marcador de fim só deve existir quando houver real ambiguidade ou compartilhamento de final.

## What Changes

- **Regra Estrita de Desambiguação Sob Demanda**:
  - Um nó final de rota **SÓ DEVE** receber círculo identificador de topo (`FIM_TOP` com letra alfabética `A`, `B`, `C`...) se atender a pelo menos uma das seguintes condições topológicas:
    1. **Convergência no mesmo final**: duas ou mais rotas terminam exatamente no mesmo ponto final.
    2. **Bifurcação / Separação ("dois finais para o mesmo início")**: duas ou mais rotas compartilham o início ou um trecho/nó comum do traçado e se dividem em finais distintos.
  - **Rotas Únicas / Isoladas**: rotas sem nenhuma junção ou separação com outra rota permanecem com o nó final como `PASSAGEM` e rótulo vazio (`rotulo = ""`), sem círculo de topo.
- **Topologia de Trajetos (`editor/core/topologia_trajeto.py`)**:
  - Refatoração da função `desambiguar_topos` para mapear o grafo de conectividade entre rotas e aplicar letras exclusivamente aos topos que demandam desambiguação.
  - Limpeza retroativa de topos: se uma rota que possuía variante voltar a ser isolada (ex: por exclusão ou Undo da variante), seu topo é automaticamente restaurado para `PASSAGEM` sem rótulo.
- **Testes e Garantia de Qualidade**:
  - Novos testes unitários em `editor/core/topologia_trajeto_test.py` cobrindo cenários com múltiplas rotas isoladas simultâneas, convergências, bifurcações e mapas mistos.
  - Testes de integração em `editor/views/jornada_rotas_integracao_test.py` e `editor/controllers/mapas_controller_test.py` validando o fluxo interativo do editor e a integridade de Undo/Redo.

## Capabilities

### Modified Capabilities
- `editor-mapas`: Refina os requisitos de desenho e anotação de traçados de rotas para formalizar a regra estrita de desambiguação de topos sob demanda, proibindo a atribuição automática de letras a rotas isoladas.

## Impact

- **Código Afetado**:
  - `editor/core/topologia_trajeto.py`
  - `editor/core/topologia_trajeto_test.py`
  - `editor/controllers/mapas_controller.py`
  - `editor/controllers/mapas_controller_test.py`
  - `editor/views/jornada_rotas_integracao_test.py`
- **Compatibilidade**: Compatibilidade total com o modelo Protobuf (`croqui.proto`) e com os compiladores existentes. Não altera esquemas nem gera incompatibilidades com versões anteriores do banco de dados.
