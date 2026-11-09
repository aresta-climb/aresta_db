# Design

## Context

Consulte `proposal.md` para motivação e `specs/` para os requisitos normativos.

Atualmente:
1. Em `aresta_api/proto/croqui.proto`, apenas `NoTrajeto` (e `MarcadorCompilado`) possuem o campo `int32 tamanho_fonte`, enquanto `Mapa.PontoDeInteresse` possui `string texto_visivel = 11`, mas não possui `tamanho_fonte`. Em `editor/views/widget_editor_mapas.py`, `BaseItemPOI.configurar_comum` instancia `self.item_texto` com `QFont("Arial", 12, QFont.Weight.Bold)` fixo, ignorando tanto o tamanho geométrico da área (`circulo`, `retangulo`, `quadrado`) quanto qualquer tentativa de ajuste manual pelo usuário.
2. Em `editor/controllers/croqui_controller.py`, o método `migrar_escalada(setor_origem, indice_origem, setor_destino, indice_destino)` já realiza a transferência atômica de uma `Escalada` entre dois `Setor` preservando o `uid` e imagens em RAM via `CmdMacro`. Contudo, em `editor/views/widget_editor_dados.py`, `_executar_soltura_arvore` interrompe qualquer operação entre pais diferentes na linha `if origem_tipo != "setor": return False`, e `editor/core/migracao_setor.py` não permite soltar uma `escalada` diretamente sobre um nó `Setor` ou sobre o agrupador `Escaladas`.

## Goals / Non-Goals

**Goals:**
- Estender `Mapa.PontoDeInteresse` no Protobuf com `int32 tamanho_fonte = 14`.
- Prover cálculo puro e determinístico de tamanho de fonte automático proporcional à geometria do POI (`circulo`, `retangulo`, `quadrado`) em `editor/core/geometrias_poi.py`, usado sempre que `tamanho_fonte` for `0` (ausente).
- Permitir edição manual de `tamanho_fonte` em `BaseItemPOI` via `DialogoEdicaoPOI` (`0 = Automático` ou `4..100 pt`) e via ação `"Tamanho da Fonte..."` no menu de contexto de todos os POIs, com Undo/Redo completo.
- Atualizar em tempo real a fonte e a posição centralizada do `texto_visivel` durante o redimensionamento (`Ctrl + arrastar`) de `ItemBoundingRetangulo`, `ItemBoundingCirculo` e `ItemBoundingQuadrado`.
- Conectar o Drag-and-Drop de `Escalada` na árvore (`ArvoreDadosTreeView` / `WidgetEditorDados._executar_soltura_arvore`) ao método `CroquiController.migrar_escalada`, permitindo soltar entre escaladas de outro setor, antes de `+ Adicionar Escalada`, sobre o agrupador `Escaladas` ou diretamente sobre o nó `Setor`.

**Non-Goals:**
- Migração automática de referências de mapa quando uma escalada muda de setor (referências de mapa apontam por `alvo_uid` descentralizado e permanecem íntegras independentemente do setor onde a escalada está listada).
- Alteração do formato de `NoTrajeto`, que já possui seu próprio `tamanho_fonte`.

## Decisions

### Decisão 1: Fórmula pura de cálculo automático de `tamanho_fonte` em `geometrias_poi.py`
- **Escolha**: Seguindo o Princípio II (Library-First), extrair para `editor/core/geometrias_poi.py` a função pura `calcular_tamanho_fonte_poi(pt_dict: dict[str, Any]) -> int`.
  - Se `int(pt_dict.get("tamanho_fonte", 0) or 0) > 0`, retorna esse valor explícito.
  - Caso contrário (`0` / automático), calcula a fonte a partir da dimensão característica da geometria e do comprimento do texto (`n = max(1, len(texto_visivel))`):
    - `circulo`: equivalente a `AlcaNoTrajeto` (`r = raio`), escalando para caber no diâmetro `2 * r`.
    - `quadrado`: usa `r_eq = lado / 2.0`, garantindo que o texto caiba tanto na altura (`lado * 0.65`) quanto na largura (`lado / (0.65 * n)`).
    - `retangulo`: calcula o limite vertical (`largura * 0.65`) e o limite horizontal (`comprimento / (0.65 * n)`), adotando ` clamp(round(min(lim_v, lim_h)), 6, 72) `.
    - `poligono` ou `linha`: padrão `12` quando `tamanho_fonte == 0`.
- **Alternativa considerada**: Acoplar o cálculo diretamente dentro de `QGraphicsTextItem` usando `fontMetrics` na View. Rejeitada porque dificulta testes unitários puros sem instanciar fontes do sistema operacional e cria variações entre plataformas.

### Decisão 2: Interface de edição de `tamanho_fonte` em `DialogoEdicaoPOI` e Menu de Contexto
- **Escolha**:
  - Em `DialogoEdicaoPOI`, adicionar um `QSpinBox` (`input_tamanho_fonte`) com intervalo `0` a `100`, `specialValueText="Automático (Pela Caixa)"` (quando valor = `0`) e sufixo `" pt"`.
  - Em `BaseItemPOI.tratar_menu_contexto`, adicionar a ação `"Tamanho da Fonte ({tam}pt)..."` (ou `"Tamanho da Fonte (Auto: {tam}pt)..."`), abrindo um `QInputDialog.getInt` (permite `0` para restaurar automático, ou `4` a `100` para fixar manual) e registrando a mutação via `registrar_movimento_final` (`QUndoStack`).
- **Alternativa considerada**: Permitir alterar `tamanho_fonte` apenas pelo diálogo de renomear. Rejeitada para manter consistência de UX com `AlcaNoTrajeto`, que oferece a ação diretamente no menu de contexto do botão direito.

### Decisão 3: Regras de validação e soltura de `Escalada` entre `Setor` na Árvore de Dados
- **Escolha**:
  - Em `editor/core/migracao_setor.py`, atualizar `validar_movimento_permitido(origem_tipo, destino_tipo, eh_sobre_item, campo_destino="")`:
    - Quando `origem_tipo == "escalada"`:
      - Permite soltar entre itens (`not eh_sobre_item`) quando `destino_tipo == "escalada"` ou quando `destino_tipo == "no_adicao"` pertencente ao campo `"escaladas"`.
      - Permite soltar sobre o item (`eh_sobre_item`) quando `destino_tipo in {"setor", "arquivosetor"}` ou quando `destino_tipo == "expando"` e o campo do expando for `"escaladas"`.
      - Rejeita qualquer outro alvo (ex: soltar escalada entre setores ou sobre um grupo).
  - Em `ProtobufTreeViewAdapter.flags`, habilitar `Qt.ItemFlag.ItemIsDropEnabled` também para nós cuja mensagem resolvida seja `Setor` ou `ArquivoSetor`.
  - Em `WidgetEditorDados._executar_soltura_arvore`:
    - Quando `eh_sobre_item` e `origem_tipo == "escalada"` sobre um `Setor`, resolver `pai_destino = msg_destino_res`, `campo_destino = "escaladas"` e `indice_destino = len(pai_destino.escaladas)`.
    - Quando `pai_origem != pai_destino` e `origem_tipo == "escalada"`, chamar `self.controller.migrar_escalada(setor_origem=pai_origem, indice_origem=indice_origem, setor_destino=pai_destino, indice_destino=indice_destino)`, expandir o setor e o nó `Escaladas` de destino e selecionar a escalada migrada na árvore.

## Risks / Trade-offs

- **[Risco: Soltura de item sobre botão `+ Adicionar` de outra coleção incompatível]** → *Mitigação*: Passar o nome do campo (`campo_destino`) para `validar_movimento_permitido`, garantindo que uma `escalada` só possa ser solta antes de `+ Adicionar Escalada` (`campo_destino == "escaladas"`) e um `setor` apenas em `setores` ou `setores_ou_grupos`.
- **[Risco: Cache de formulário desatualizado ao migrar escalada entre setores]** → *Mitigação*: Chamar `self._descartar_cache_recursivo(node_origem)` antes de `self.controller.migrar_escalada(...)`, exatamente como já é feito na migração de setores e na reordenação.
