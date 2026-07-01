## Context

O Editor de Mapas atual carece de uma interface visual dedicada à gestão e edição interativa das "Referências" (conexões entre formas no mapa e as entidades lógicas como setores, vias e grupos). Essa modificação envolve introduzir novos componentes de UI (`WidgetEditorMapas`), interceptação de cliques do mouse no `GraphicsScene`, e manipulação do modelo Protobuf via comandos de histórico (`QUndoStack`) gerenciados pelo `MapasController`.

## Goals / Non-Goals

**Goals:**
- Implementar um Painel de Referências no lado direito do Editor de Mapas interagindo em sincronia bidirecional com o `CroquiModel`.
- Fornecer um "Modo de Linkagem" interativo, no qual os cliques nas formas do mapa selecionam os respectivos `ids` e os vinculam à Referência ativa.
- Exibição em modo normal: destacar no mapa (via highlight visual) os objetos associados a uma Referência quando o cursor paira sobre ela no painel.
- Adicionar ferramenta de ajuste de câmera com overlay `WYSIWYG` simulando a tela móvel (16:9 proporção vertical ou equivalente do app), incluindo cortes (sombras) de 20% acima e abaixo.
- Aderir restritamente ao padrão MVC: `Widget` -> `MapasController` -> `QUndoStack` (Comandos) -> `CroquiModel`.

**Non-Goals:**
- Alterações no Protobuf (`croqui.proto`), pois a estrutura de `Referencia` e `AjusteDeCamera` existente já tem suporte a todos os requisitos propostos.
- Edição de referências em texto puro / YAML na UI nova.

## Decisions

1. **Uso de Comandos Genéricos (MapasController):** 
   - *Decisão:* Reutilizar `CmdAdicionarRepeated`, `CmdAlterarRepeatedItem`, e `CmdRemoverRepeated` no `MapasController` tendo a propriedade `referencias` como alvo.
   - *Rationale:* Evita replicação de lógica de Undo/Redo e se apoia no sistema robusto que já existe para POIs (Pontos de Interesse).

2. **Ajuste de Câmera com Overlay Físico:**
   - *Decisão:* A UI desenhará um "guideline box" com proporção exata da tela quando em modo de câmera. Um sombreamento (`darken overlay`) nos primeiros 20% do topo e últimos 20% da base indicará as bordas parcialmente ocultas (por cabeçalho do app ou painel de abas).
   - *Rationale:* Fornecer feedback visual exato ao invés de configurar floats matemáticos cegamente no Protobuf.

3. **Busca Global Integrada (CroquiModel):**
   - *Decisão:* O Modal de busca varrerá toda a árvore do `CroquiModel` para encontrar alvos possíveis. Como a memória do modelo de croquis não é imensa para um editor desktop, isso ocorrerá sem lentidão.
   - *Rationale:* Garante dados 100% lincados com objetos que de fato existem, eliminando erros de digitação.

## Risks / Trade-offs

- **[Risk] Complexidade de Máquina de Estados na UI:** Inserir o "Modo Linkagem" e o "Modo Ajuste de Câmera" aumenta a complexidade de eventos de mouse na View.
  - *Mitigation:* Isolar os handlers de mouse em classes de `InteractionStrategy` se o código principal do Scene ficar longo.

- **[Risk] Atualização incremental (Performance):** Re-renderizar o painel direito a cada mudança de ID.
  - *Mitigation:* Atualizar apenas o item / card específico modificado. O Controller emite sinais granulares.
