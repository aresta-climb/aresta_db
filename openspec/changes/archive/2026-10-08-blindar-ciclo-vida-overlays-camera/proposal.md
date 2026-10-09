# Proposal: Blindagem do Ciclo de Vida de Overlays de Câmera no Editor de Mapas

## Why

Durante a operação do Editor de Mapas, passar o cursor sobre cards de referências ou acionar o modo de enquadramento de câmera instancia itens visuais de sobreposição (`ItemCameraOverlay`). Quando a cena gráfica do Qt sofre recarregamentos, substituição ou limpeza (`cena.clear()`, troca de mapa em `set_mapa_atual`, ou `descarregar_mapa`), os objetos gráficos C++ subjacentes são destruídos fisicamente pelo motor do Qt. No entanto, o wrapper em Python continuava retido em `self.item_hover_camera_overlay` e `self.item_camera_overlay`, cuja avaliação booleana em Python permanece `True`. 

Com isso, o próximo evento de destaque visual (`destacar_pois_temporariamente`), encerramento de destaque (`remover_destaque_pois`) ou entrada em modo de câmera tenta acessar ou alterar propriedades do objeto destruído (`setVisible()`, `setRect()`, `setPos()`), causando falha fatal no Shiboken (`RuntimeError: libshiboken: Internal C++ object (ItemCameraOverlay) already deleted`), conforme capturado em ambiente de produção via Sentry. Esta mudança é necessária para blindar completamente o ciclo de vida desses itens temporários e sanar a vulnerabilidade antes do lançamento da versão `0.3.14`.

## What Changes

- **Limpeza Ativa no Ciclo de Vida da Cena**:
  - Garantir anulação explícita (`None`) e remoção segura de `item_hover_camera_overlay` e `item_camera_overlay` em `cancelar_modos_interativos()`, `descarregar_mapa()`, `set_mapa_atual()` e antes de invocar `cena.clear()` em `_renderizar_mapa()`.
- **Validação com `shiboken6.isValid()` e Pertinência à Cena**:
  - Em `destacar_pois_temporariamente()`, validar se `item_hover_camera_overlay` ainda é válido em C++ e se pertence à cena ativa (`item.scene() == self.visualizador.scene()`) antes de tentar reutilizá-lo ou chamar `.setVisible(True)` / `.setVisible(False)`. Caso seja inválido ou pertença a cena defasada, recriar a instância do zero associada à cena gráfica ativa.
  - Em `iniciar_modo_camera()`, validar analogamente `self.item_camera_overlay` com `shiboken6.isValid()` e correspondência de cena antes de tentar torná-lo visível.
- **Defensividade em `remover_destaque_pois()`**:
  - Preservar a anulação incondicional de `item_hover_camera_overlay` e a remoção segura via `_remover_item_seguro()`, estendendo o tratamento preventivo de exceções.
- **Suíte de Testes Automatizados TDD**:
  - Adicionar testes de estresse em `widget_editor_mapas_test.py` reproduzindo hover e destaques de câmera após `cena.clear()`, trocas de mapas e descarregamentos, assegurando 100% de cobertura e impedindo regressões.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida. -->

### Modified Capabilities
- `editor-mapas`: Expandir o requisito de integridade de ciclo de vida e cancelamento seguro de modos interativos para incluir explicitamente a governança de sobreposições de câmera (`ItemCameraOverlay`), validação de ponteiros C++ e prevenção de acessos a itens pós-limpeza de cena.

## Impact

- **Código Afetado**: `editor/views/widget_editor_mapas.py` e sua respectiva suíte de testes `editor/views/widget_editor_mapas_test.py`.
- **APIs e Modelos**: Nenhuma alteração em esquemas Protobuf, regras de persistência ou contratos de dados.
- **Compatibilidade**: Estritamente interno à camada de visão gráfica PySide6; melhora a estabilidade em todas as plataformas suportadas (Windows, Linux Flatpak e macOS).
