# Proposal

## Why

Ao clicar nos botões de ação rápida do Painel de Qualidade do Croqui (como `"Adicionar link Google Maps"` ou `"Gerar mapa de pontos"`), a aba "Dados" abre o formulário do Pico no topo sem rolar até o campo alvo quando o formulário ainda não está em cache, quando a aba "Dados" nunca foi exibida ou quando uma seção `"Opções Avançadas"` acaba de ser expandida — porque o `QScrollArea` do Qt ainda possui eventos pendentes de `ShowToParent`/`LayoutRequest` no momento em que `ensureWidgetVisible` é executado sincronicamente. Além disso, a tarefa `"Mapa de pontos de estrada dos picos"` (`etapa1_malha_estrada_picos`) aparece por último (`1.8`) na Etapa 1, distante de `"Localização e Google Maps dos picos"` (`1.2`), e seu botão aponta para `/campo:localizacao` (focando `Latitude`) em vez de focar diretamente o botão `"Gerar Mapa de Pontos"`.

## What Changes

- **Garantia de scroll após estabilização de layout na aba Dados**: Ajustar `WidgetFormularioPadrao.load_node` para anexar o `container` ao `QScrollArea` somente após montar seus campos, ativar o layout com `adjustSize()` e confirmar `ensureWidgetVisible` + `setFocus` de forma coalescida no giro seguinte do *event loop* (`QTimer.singleShot(0)`, sem uso de `QApplication.processEvents()`), cobrindo primeira abertura de nó, primeira exibição da `PaginaDados` e auto-expansão de `WidgetSecaoAvancada`.
- **Foco direto no botão `"Gerar Mapa de Pontos"` via `/campo:malha_estrada`**: Mapear o sufixo `/campo:malha_estrada` em `WidgetFormularioPadrao.focar_campo` para localizar o card `localizacao` do Pico e transferir o foco diretamente para `btn_gerar_malha` (`"Gerar Mapa de Pontos"`) quando habilitado.
- **Reordenação da Etapa 1 no Painel de Qualidade e no relatório de saúde**: Mover a tarefa `etapa1_malha_estrada_picos` (`"Mapa de pontos de estrada dos picos"`) para a posição `1.3`, imediatamente abaixo de `1.2 Localização e Google Maps dos picos` (deslocando as tarefas seguintes para `1.4`–`1.8`), mantendo o card `1.2` focado apenas em coordenadas e Google Maps; emitir `/campo:malha_estrada` nas ações `"Gerar mapa de pontos"` e `"Atualizar mapa de pontos"` (mantendo `/campo:localizacao` quando faltar coordenada); atualizar `COLUNAS_TAREFAS_PAINEL` em `scripts/medir_saude_croquis.py` com invalidação segura de cabeçalhos desatualizados durante leitura incremental.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-dados-formularios`: Exigir confirmação assíncrona coalescida do scroll (`QTimer.singleShot(0)`) após o layout do `QScrollArea` estabilizar em primeira abertura de aba/nó e expansão de `Opções Avançadas`, e adicionar suporte a `/campo:malha_estrada` para rolar até `localizacao` e focar o botão `"Gerar Mapa de Pontos"`.
- `painel-nota-qualidade-croqui`: Posicionar `etapa1_malha_estrada_picos` como critério `1.3` (logo após `1.2 Localização e url_google_maps dos picos`), ajustar as URIs das ações `"Gerar mapa de pontos"` e `"Atualizar mapa de pontos"` para `/campo:malha_estrada`, e refletir a nova numeração das colunas da Etapa 1 no relatório de saúde.

## Impact

- `editor/views/widget_editor_dados.py` e `editor/views/widget_editor_dados_test.py`
- `editor/core/avaliador_nota_qualidade.py` e `editor/core/avaliador_nota_qualidade_test.py`
- `scripts/medir_saude_croquis.py` e `scripts/medir_saude_croquis_test.py`
- `openspec/specs/editor-dados-formularios/spec.md` e `openspec/specs/painel-nota-qualidade-croqui/spec.md`
