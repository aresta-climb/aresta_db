# Design: Blindagem do Ciclo de Vida de Overlays de Câmera

## Context

No `WidgetEditorMapas`, as sobreposições de enquadramento de câmera (`ItemCameraOverlay: QGraphicsRectItem`) são utilizadas em dois contextos:
1. `self.item_hover_camera_overlay`: desenhado transitoriamente quando o usuário passa o mouse sobre cards de referências no `PainelReferencias` (`destacar_pois_temporariamente`).
2. `self.item_camera_overlay`: desenhado de forma interativa quando o usuário entra no modo de ajuste de câmera 9:16 (`iniciar_modo_camera`).

Ambos os itens são inseridos na `QGraphicsScene` ativa do mapa (`self.visualizador.scene()`). Conforme demonstrado em `proposal.md`, quando a cena sofre `cena.clear()` ou quando uma nova cena é instanciada (em `set_mapa_atual`, `descarregar_mapa` ou `_renderizar_mapa`), a camada C++ do Qt desaloca os nós gráficos. Os wrappers Python correspondentes continuam existindo na memória do processo e sua checagem booleana padrão em Python (`if self.item_hover_camera_overlay:`) retorna `True`. Qualquer invocação subsequente de métodos C++ (`setVisible`, `setRect`, `setPos`) gera `RuntimeError: libshiboken: Internal C++ object (ItemCameraOverlay) already deleted`.

## Goals / Non-Goals

**Goals:**
- Proteger todas as leituras, visibilidades e mutações de `item_hover_camera_overlay` e `item_camera_overlay` contra desreferenciamento de ponteiros C++ deletados.
- Anular formalmente (`= None`) e desvincular de forma segura esses itens em todos os pontos de transição de cena (`cancelar_modos_interativos`, `descarregar_mapa`, `set_mapa_atual`, `_renderizar_mapa`).
- Garantir que `destacar_pois_temporariamente` e `iniciar_modo_camera` re-instanciem os overlays de forma transparente caso detectem perda de validade em C++ ou divergência com a cena ativa.
- Manter 100% de cobertura de testes unitários sem impactos de performance na interface.

**Non-Goals:**
- Não alterar as regras matemáticas de conversão de coordenadas ou proporção 9:16 da câmera.
- Não alterar comandos de histórico (`QUndoCommand`) ou modelos Protobuf.

## Decisions

### Decisão 1: Helper Defensivo de Integridade de Item Gráfico (`_item_grafico_valido`)

Criar método utilitário em `WidgetEditorMapas` para inspecionar rigorosamente se um item gráfico Qt ainda existe fisicamente e pertence à cena atual:

```python
def _item_grafico_valido(self, item: Any, cena_esperada: Optional[Any] = None) -> bool:
    """Verifica se um QGraphicsItem possui ponteiro C++ válido e pertence à cena esperada."""
    if item is None:
        return False
    try:
        if shiboken6 is not None and hasattr(shiboken6, "isValid"):
            if not shiboken6.isValid(item):
                return False
        if cena_esperada is not None:
            if not hasattr(item, "scene") or item.scene() != cena_esperada:
                return False
        elif hasattr(item, "scene") and item.scene() is None:
            return False
        return True
    except Exception:
        return False
```

*Alternativa considerada*: Usar apenas blocos `try/except RuntimeError` ao redor de cada chamada a `.setVisible()`.
*Razão da escolha*: A checagem proativa via `shiboken6.isValid()` e verificação de cena é limpa, declarativa e evita ruídos desnecessários de exceções em debuggers ou handlers globais de telemetria.

### Decisão 2: Governança do Ciclo de Vida em Transições de Cena

Garantir que a limpeza dos overlays seja executada proativamente:
1. Em `cancelar_modos_interativos()`:
   ```python
   if hasattr(self, "item_hover_camera_overlay") and self.item_hover_camera_overlay:
       self._remover_item_seguro(self.item_hover_camera_overlay)
       self.item_hover_camera_overlay = None
   if hasattr(self, "item_camera_overlay") and self.item_camera_overlay:
       self._remover_item_seguro(self.item_camera_overlay)
       self.item_camera_overlay = None
   ```
2. Em `descarregar_mapa()` e `set_mapa_atual()`: invocar `cancelar_modos_interativos()` e assegurar reset desses atributos para `None`.
3. Em `_renderizar_mapa()`: executar `cancelar_modos_interativos()` antes de invocar `cena.clear()`.

### Decisão 3: Revalidação e Re-instanciação Transparente em `destacar_pois_temporariamente` e `iniciar_modo_camera`

Em `destacar_pois_temporariamente`:
- Ao desenhar câmera estática (`ajuste_de_camera.zoom > 0`):
  - Verificar se `self.item_hover_camera_overlay` é válido e pertence à cena ativa (`cena_atual = self.visualizador.scene()`).
  - Se inválido ou ausente, criar nova instância de `ItemCameraOverlay()` e adicioná-la à `cena_atual`.
- No ramo alternativo (quando a referência não tem ajuste de câmera):
  - Verificar se `self.item_hover_camera_overlay` é válido antes de chamar `.setVisible(False)`. Se for inválido, apenas definir `self.item_hover_camera_overlay = None`.

Em `iniciar_modo_camera`:
- Verificar se `self.item_camera_overlay` é válido e pertence a `self.visualizador.scene()`. Se inválido, criar nova instância e adicioná-la à cena.

## Risks / Trade-offs

- **[Risco]** Mocks em testes unitários que não usem instâncias C++ reais poderiam ser falsamente rejeitados por `shiboken6.isValid()`.
  - *Mitigação*: O helper `_item_grafico_valido` usa fallback defensivo `try/except` e, caso o mock não seja do Shiboken, valida a presença dos atributos essenciais sem quebrar suítes sintéticas.
