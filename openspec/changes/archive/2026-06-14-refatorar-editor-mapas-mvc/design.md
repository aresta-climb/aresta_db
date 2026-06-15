## Context

O `WidgetEditorMapas` atual tem responsabilidades de View, Model (via `mapas_lib.py`) e Controller/Commands (via `CmdMoverPonto`). Ele lê arquivos YAML, mantêm o estado dos POIs cruzes num dicionário local e lida com histórico sem se comunicar com o `CroquiModel` ou o Protobuf underlying.
A refatoração tem como objetivo alinhar o Editor de Mapas com a arquitetura estabelecida do sistema: Modelos (Proxy/Protobuf), Controllers puros que não sabem de GUI, Commands isolados que injetam modificações via QUndoStack e Views que apenas refletem os modelos e delegam intenções.

## Goals / Non-Goals

**Goals:**
- Desacoplar a View da manipulação de arquivos do FileSystem (remover `caminho_pasta`).
- Centralizar Comandos de manipulação do mapa (`commands/comandos_mapas.py`).
- Otimizar renderização granular atrelando `idx_poi` ao `QGraphicsItem`.
- Impor rigidez no `arquitetura_mvc_test.py`.

**Non-Goals:**
- Não iremos refatorar o `WidgetEditorDados` ou outros editores.
- Não adicionaremos novas features ao mapa (como zoom interativo ou suporte a rotas), o comportamento do usuário final continua o mesmo.

## Decisions

1. **MapasController Dedicado**: Criaremos um `MapasController` separado ao invés de inchar o `CroquiController`. Ele será instanciado no topo (pelo `WidgetEditorDados`) e injetado de cima pra baixo, contendo a referência ao `CroquiModel` e à `QUndoStack`.
2. **Migração do converter_box_para_circulo**: A função será movida do antigo `mapas_lib.py` para o `MapasController`, já que atua na transformação lógica antes de persistir o dado.
3. **Comunicação Model -> View via Proxy**: A view não manipulará dicionários YAML. O `WidgetEditorDados` chamará `widget_mapas.set_mapa_atual(msg_mapa, pico_idx, grupo_idx, mapa_idx)`. A View vai escutar eventos `repeated_item_alterado` do Model para repintar os itens.
4. **Rastreamento de Índice Avançado na View**: Como os mapas possuem poucos POIs mas a performance é crítica no mouse drag, manteremos um dicionário `idx_poi -> QGraphicsItem` na View. Quando houver inserções ou deleções, faremos um reajuste algorítmico nas chaves deste dicionário para manter a paridade com o modelo Protobuf, sem reconstruir toda a tela.
5. **Carregamento de Imagem**: A view chamará `self.mapas_controller.obter_caminho_imagem_mapa(msg_mapa)` para saber qual arquivo usar no background (`QPixmap`), retirando a dependência do `caminho_db` local.

## Risks / Trade-offs

- **Complexidade de Índices (Risco)**: O reajuste manual de chaves num dicionário na View durante inserção/deleção é logicamente delicado e propenso a off-by-one errors.
  *Mitigação*: Escreveremos testes unitários focados na sincronização do dicionário na view.
- **Acoplamento com Protobuf e View (Trade-off)**: Em vez de POIs plain-text, a view estará diretamente acoplada à leitura da mensagem `Mapa` e seus signals (`dado_alterado`, `repeated_item_alterado`). É um trade-off benéfico pois remove o Middleman de YAML, padronizando a app.
