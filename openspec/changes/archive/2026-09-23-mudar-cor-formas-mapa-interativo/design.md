## Context

No editor de mapas (`editor/views/widget_editor_mapas.py`), elementos do tipo `ItemTrajetoLinha` possuem um submenu `"Mudar Cor"` interativo com paleta pré-definida (`PALETA_CORES_ROCHA`) e diálogo de cor personalizada. Por outro lado, as formas de área de interesse (`ItemBoundingCirculo`, `ItemBoundingRetangulo`, `ItemBoundingQuadrado`, `ItemBoundingPoligono`) utilizam caneta e pincel estáticos, sem expor a seleção de cor no menu de contexto nem atualizar suas cores visuais mesmo quando o campo `cor` está preenchido no dicionário de dados.

## Goals / Non-Goals

**Goals:**
- Criar um helper compartilhado `montar_submenu_cores` em `widget_editor_mapas.py` para construir de forma padronizada o menu de cores para linhas e formas geométricas.
- Adicionar a opção "Padrão do Sistema" no submenu de cores das formas geométricas para resetar o elemento para as cores originais translúcidas (verde para círculos/retângulos e azul para polígonos).
- Implementar o método `atualizar_estilo_visual` em `BaseItemPOI`, chamado na inicialização, em `carregar_de_dict` e ao alterar a cor.
- Fazer com que as alças de vértices de polígonos (`AlcaVertice`) assumam dinamicamente a cor da forma.
- Padronizar o menu de contexto de `ItemBoundingPoligono` eliminando código duplicado e garantindo suporte a Undo/Redo via `registrar_movimento_final`.
- Assegurar 100% de cobertura de testes unitários para todas as novas ramificações e fluxos de interação.

**Non-Goals:**
- Alterações no schema Protobuf (`croqui.proto`), pois o campo `string cor = 10` já existe nativamente em `PontoDeInteresse`.
- Configuração de espessura de traço ou estilo tracejado para círculos, retângulos ou polígonos (esses continuam exclusivos para linhas/trajetos).

## Decisions

### Decisão 1: Helper Compartilhado `montar_submenu_cores`
- **Decisão**: Extrair a lógica de construção do menu de cores para a função `montar_submenu_cores(menu: QMenu, cor_atual: Optional[str], callback_definir: Callable[[str], None], callback_personalizada: Callable[[], None], callback_padrao: Optional[Callable[[], None]] = None) -> QMenu`.
- **Racional**: Elimina a duplicação entre `ItemTrajetoLinha` e `BaseItemPOI`, garantindo que novos elementos ou alterações futuras na paleta afetem todos os componentes de forma coerente.
- **Alternativas**: Duplicar os blocos de `menu.addMenu("Mudar Cor")` em cada classe; rejeitado por violar o princípio DRY e aumentar custos de manutenção.

### Decisão 2: Opção "Padrão do Sistema"
- **Decisão**: Disponibilizar `"Padrão do Sistema"` como primeira opção do submenu para formas geométricas. Se `cor` não estiver definida em `pt_dict`, essa opção exibirá o marcador ativo (`● `). Ao ser clicada, remove a chave `'cor'` do elemento, chama `carregar_de_dict` e grava no histórico com `registrar_movimento_final`.
- **Racional**: Permite que o usuário reverta uma cor customizada sem precisar adivinhar o hexadecimal padrão ou editar arquivos YAML manualmente.
- **Alternativas**: Deixar que o usuário escolha Verde Lima ou Ciano para "simular" o padrão; rejeitado porque manteria a chave `cor` gravada desnecessariamente no arquivo.

### Decisão 3: Aplicação de Estilo Visual em `BaseItemPOI`
- **Decisão**: Implementar `atualizar_estilo_visual()` em `BaseItemPOI` que resolve a cor ativa:
  - Se `pt_dict.get('cor')` existir: cor sólida para borda (`QPen(QColor(cor), 2)`) e cor com alpha 60 para preenchimento (`QBrush(QColor(r, g, b, 60))`).
  - Se não existir: utiliza a cor padrão da forma (verde `#64FF64` para círculos/retângulos e azul `#6464FF` para polígonos).
  - Atualiza as alças `AlcaVertice` do polígono caso existam.
- **Racional**: Centraliza a regra de cores na classe base, permitindo que qualquer chamada a `carregar_de_dict` (inclusive via Undo/Redo) redesenhe a forma com a cor correta.

## Risks / Trade-offs

- **[Risco]** Mutações no estado durante Undo/Redo poderiam não atualizar a cena gráfica se dependessem apenas de sinais manuais.
  - **Mitigação**: O método `_on_repeated_item_alterado` do `WidgetEditorMapas` já chama `carregar_de_dict(pt_dict)` no item existente quando um comando da `QUndoStack` é desfeito ou refeito. Como `carregar_de_dict` chamará `atualizar_estilo_visual`, a atualização visual no canvas será automática.
- **[Risco]** Conflito com testes existentes que interceptam o menu com mocks parciais.
  - **Mitigação**: Manter a assinatura de métodos auxiliares compatível e expandir testes específicos para o novo submenu de cores em `widget_editor_mapas_test.py`.
