# Design: Cancelamento Seguro de Modos Interativos e Ciclo de Vida da Cena

## Context

No `WidgetEditorMapas`, existem múltiplos fluxos interativos de anotação e desenho direto sobre o canvas do mapa:
- **`modo_desenho`**: criação interativa de polígonos ponto a ponto com preview vetorial (`item_desenho_temp: QGraphicsPathItem`) e alças (`alcas_desenho_temp: List[QGraphicsEllipseItem]`).
- **`modo_nova_rota`**: traçado de rotas com nós e miradores de snap (`item_desenho_nova_rota_temp`, `item_mira_snap`, `alcas_desenho_nova_rota_temp`).
- **`modo_conversao`**: seleção retangular de área (`item_selecao`).
- **`modo_camera`** e **`modo_linkagem`**: sobreposições temporárias e destaques de POIs vinculados a referências.

Os itens visuais temporários desses modos são adicionados diretamente em `dados['cena']` (uma instância de `CenaDesenho(QGraphicsScene)`). No entanto, o ciclo de vida da cena é volátil:
1. `set_mapa_atual(...)` instancia uma nova `CenaDesenho(self)`.
2. `_renderizar_mapa(...)` executa `cena.clear()`.
3. `descarregar_mapa(...)` executa `cena.clear()` e descarta a cena ativa.
4. Sinais reativos do modelo (`CroquiModel.repeated_removido`, `imagem_alterada`) podem invocar `_atualizar_lista_mapas` ou recarregar a cena.

Quando `cena.clear()` ou a destruição da cena anterior ocorre, a camada C++ do Qt desaloca todos os itens filhos. Como as flags de controle (`self.modo_desenho`, `self.modo_nova_rota`) não eram limpas nessas transições de cena, os ponteiros em Python permaneciam referenciando a memória C++ já liberada, resultando no crash do Shiboken no clique seguinte.

## Goals / Non-Goals

**Goals:**
- Centralizar o cancelamento de todos os modos interativos em uma rotina unificada e à prova de falhas (`cancelar_modos_interativos()`).
- Garantir que qualquer recarregamento (`carregar_mapa`, `_renderizar_mapa`), seleção de outro mapa (`set_mapa_atual`) ou descarregamento (`descarregar_mapa`) encerre modos temporários antes de manipular a cena.
- Tornar os métodos de descarte (`cancelar_modo_desenho`, `cancelar_modo_nova_rota`) defensivos contra itens gráficos C++ já destruídos, utilizando `shiboken6.isValid()`.
- Garantir guardas de integridade em `adicionar_ponto_desenho`, `adicionar_ponto_nova_rota` e `mouseMoveEvent` (snap) para evitar desreferenciamento de ponteiros inválidos.
- Manter 100% de cobertura de testes unitários sem regressões nos fluxos existentes.

**Non-Goals:**
- Não alterar a experiência do usuário durante o desenho normal (atalhos Enter/Esc/duplo clique permanecem com idêntico comportamento).
- Não alterar schemas Protobuf, persistência YAML ou regras de negócio do `CroquiModel`.

## Decisions

### Decisão 1: Método Unificado `cancelar_modos_interativos()`

Criar um método helper de ciclo de vida em `WidgetEditorMapas`:
```python
def cancelar_modos_interativos(self) -> None:
    if getattr(self, 'modo_desenho', False):
        self.cancelar_modo_desenho()
    if getattr(self, 'modo_nova_rota', False):
        self.cancelar_modo_nova_rota()
    if getattr(self, 'modo_conversao', False):
        self.modo_conversao = False
        if hasattr(self, 'item_selecao') and self.item_selecao:
            self._remover_item_seguro(self.item_selecao)
            self.item_selecao = None
            self.selection_item = None
        self.visualizador.unsetCursor()
        self.label_modo.setVisible(False)
    if getattr(self, 'modo_camera', False):
        self.parar_modo_camera()
    if getattr(self, 'modo_linkagem', False):
        self.parar_modo_linkagem()
```
Pontos de invocação:
1. No início de `set_mapa_atual(...)`.
2. No início de `descarregar_mapa(...)`.
3. No início de `_renderizar_mapa(...)`, antes de invocar `cena.clear()`.
4. Ao iniciar um novo modo (ex: `iniciar_modo_desenho` cancela antes `modo_nova_rota` e vice-versa, impedindo modos conflitantes simultâneos).

*Alternativa considerada*: Cancelar apenas dentro do `cena.clear()`.
*Razão da escolha*: Iniciar a limpeza antes desacopla os widgets visuais (cursores, painel de status `label_modo`) da própria cena e garante que `removeItem` seja chamado enquanto a cena ainda existe.

### Decisão 2: Descarte Defensivo com `shiboken6.isValid()`

Para evitar que `cena.removeItem(item)` levante `RuntimeError` caso a cena já tenha sido limpa por eventos externos:
```python
import shiboken6

def _remover_item_seguro(self, item: Any) -> None:
    if not item:
        return
    try:
        valido = getattr(shiboken6, "isValid", lambda obj: True)(item)
        if valido and self.dados_atuais and 'cena' in self.dados_atuais:
            cena = self.dados_atuais['cena']
            if cena and item.scene() == cena:
                cena.removeItem(item)
    except Exception:
        pass
```
*Alternativa considerada*: Confiar apenas na ordem sequencial de chamadas.
*Razão da escolha*: Em sistemas orientados a eventos com Qt e garbage collection assíncrono, a verificação explícita de validade de ponteiro C++ pelo Shiboken é a prática recomendada pela The Qt Company para prevenir crashes silenciosos ou falhas em testes com mocks.

### Decisão 3: Verificação de Integridade em Eventos de Mouse

Em `adicionar_ponto_desenho(self, pos: QPointF)` e `adicionar_ponto_nova_rota(self, pos: QPointF)`:
Se `self.item_desenho_temp` for `None` ou `not shiboken6.isValid(self.item_desenho_temp)` ou sua cena divergir da cena atual:
- Recriar o `QGraphicsPathItem` na cena atual e adicionar novamente os pontos existentes, ou cancelar o modo de desenho se a cena for inválida.
Isso impede que uma falha de sincronia quebre a execução do aplicativo com exceção fatal.

## Risks / Trade-offs

- **[Risco]** Cancelamento automático pode descartar o polígono inacabado se o usuário trocar de mapa antes de fechar o loop.
  - *Mitigação*: Este é o comportamento esperado; um desenho de polígono é restrito a uma única imagem. Trocar de mapa necessariamente invalida as coordenadas da imagem anterior.
- **[Risco]** Mocks de testes unitários que não usem instâncias reais de `QGraphicsItem` podem falhar ao passar por `shiboken6.isValid()`.
  - *Mitigação*: Uso de fallback `getattr(shiboken6, "isValid", lambda obj: True)` e proteção com `try/except Exception` no helper de remoção segura.
