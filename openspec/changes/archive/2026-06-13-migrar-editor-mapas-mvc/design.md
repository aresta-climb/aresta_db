## Context

Atualmente o aplicativo Aresta Editor tem o `WidgetEditorMapas` implementado como um componente fortemente acoplado aos arquivos `.md` e ao seu próprio pipeline de undo/redo. Este design diverge da arquitetura principal do MVC do `aresta_db`, causando redundância de código e impossibilitando uma experiência contínua entre editar dados de formulário e posições no mapa para o usuário. 
A arquitetura MVC já está estabelecida para o resto do aplicativo. Portanto, a intenção é portar o componente de edição visual para o padrão existente sem quebrar os recursos de mapeamento.

## Goals / Non-Goals

**Goals:**
- Desacoplar o `WidgetEditorMapas` do `GerenciadorArquivosMapa` e do acesso direto ao sistema de arquivos.
- Alimentar a sidebar iterando no `CroquiModel`.
- Integrar os comandos de edição visual (movimento, resize, etc.) usando os métodos do `CroquiController`, que alimenta a `QUndoStack` do sistema.
- Exibir a interface gráfica na janela principal como uma aba dependente dos dados abertos na árvore.

**Non-Goals:**
- Mudar o fluxo ou adicionar novos tipos de POIs (apenas vamos migrar `circular`, `box` e `area_livre`).
- Alterar o motor gráfico (`QGraphicsView/QGraphicsScene`).
- Reescrever totalmente a lógica matemática de interseção/redimensionamento dos items gráficos (eles apenas devem disparar a atualização de modelo final de maneira diferente).

## Decisions

1. **Uso de Formato MAPA no Editor Principal**
   A anotação Protobuf de formato UI ganhará o enum `MAPA`. Quando um `Mapa` for detectado no `ProtobufTreeViewAdapter`/`WidgetFormularioPadrao`, será gerado um widget contendo exclusivamente o botão "Abrir no Editor de Mapas". Clicar neste botão invocará `janela_principal.tabs.setCurrentIndex(2)` e solicitará à View do Mapa que carregue o mapa e foco correspondente.

2. **Remoção das dependências e ciclo de vida antigo do mapa**
   O `WidgetEditorMapas` atual usa `carregar_pasta()` para povoar a barra lateral. Isso será reescrito como `carregar_de_modelo(croqui_model)` onde a barra listará os `Mapa` messages aninhados na árvore. 

3. **Injeção de Controller nos Items Gráficos**
   Os subclasses de `BaseItemPOI` (como `ItemBoundingBox`) deverão, na soltura do mouse (em `mouseReleaseEvent` que atualmente invoca `registrar_movimento_final`), criar cópias atualizadas dos sub-messages `PontoDeInteresse` e disparar algo como `controller.alterar_repeated_item(mapa_msg, "pontos_de_interesse", indice_poi, velho_poi, novo_poi)`.

4. **Imperativo do TDD (Test-Driven Development)**
   Em observância aos Princípios Básicos de Desenvolvimento do repositório, toda nova lógica inserida ou migrada no processo será concebida seguindo o ciclo *Red-Green-Refactor*. A meta inegociável é manter **100% de cobertura de testes unitários**, especialmente para a orquestração do gateway do novo botão no `WidgetEditorDados` e a renderização do `WidgetEditorMapas` alimentada pela simulação do `CroquiModel`. Os testes orientarão a API de interface com os demais módulos.

## Risks / Trade-offs

- **Sincronia do Modelo e do Gráfico**: Ao aplicar "Undo" (Desfazer), a visualização pode não renderizar automaticamente se a Cena Gráfica não escutar o sinal de "campo alterado" originado do `CroquiModel`.
  - *Mitigação*: `WidgetEditorMapas` deve subscrever-se aos sinais `repeated_adicionado`, `repeated_removido`, e `repeated_item_alterado` do `CroquiModel` e, se o item impactado for do mapa atualmente visualizado, ele deve re-desenhar o item.
- **Acúmulo de Comandos**: Edições arrastando objetos no `QGraphicsView` podem causar enxurrada de chamadas se acopladas erradas.
  - *Mitigação*: Faremos como era originalmente – apenas atualizar o objeto visual durante a movimentação, enviando o comando final para o Controller somente no evento de encerramento do arraste (`mouseReleaseEvent`).
