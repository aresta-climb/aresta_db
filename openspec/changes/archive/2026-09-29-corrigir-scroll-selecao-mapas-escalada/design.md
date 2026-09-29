## Context

Veja `proposal.md` para motivação e `specs/editor-mapas-mvc-sidebar/spec.md` para os requisitos.

Atualmente, `WidgetEditorMapas` armazena dados em `self.list_widget` usando tuplas de diferentes comprimentos em `Qt.ItemDataRole.UserRole`:
- `('mapa_geral', p_idx, -1, m_idx)` (4 elementos)
- `('setor', p_idx, sg_idx, m_idx)` (4 elementos)
- `('grupo', p_idx, sg_idx, m_idx)` (4 elementos)
- `('subsetor', p_idx, sg_idx, s_idx, m_idx)` (5 elementos)
- `('escalada_setor', p_idx, sg_idx, e_idx, m_idx)` (5 elementos)
- `('escalada_subsetor', p_idx, sg_idx, s_idx, e_idx, m_idx)` (6 elementos)

No fluxo atual, o método `set_mapa_atual` não aceita `e_idx`, descartando o índice da escalada. Ao sincronizar o item visual na renderização, `selecionar_mapa_por_indices` é chamado com `s_idx=-1`, casando inadvertidamente o mapa do setor e redefinindo a seleção da lista com sinais bloqueados, gerando o salto indevido de seleção e o loop ao navegar com a tecla de seta para baixo.

## Goals / Non-Goals

**Goals:**
- Manter o rastreamento completo e inequívoco de qualquer mapa ativo no editor (`tipo`, `pico_idx`, `sg_idx`, `mapa_idx`, `s_idx`, `e_idx`).
- Garantir casamento estrito e exato em `selecionar_mapa_por_indices` contra as tuplas de `Qt.ItemDataRole.UserRole`.
- Garantir que a lista execute `scrollToItem` para manter o mapa selecionado sempre visível.
- Permitir navegação por teclado fluida (seta para baixo / cima) percorrendo todos os mapas sequencialmente sem loops.
- Corrigir a resolução de foco global em `area_principal.py` para rotas de mapas de escalada.
- Assegurar que `set_contexto` forneça o caminho completo com `expando:escaladas/item:{e_idx}` para o gerenciamento de histórico (Undo/Redo).

**Non-Goals:**
- Modificar o formato ou serialização dos arquivos Protobuf.
- Alterar o design visual ou folha de estilos dos itens da lista lateral.
- Mudar regras de negócio relativas a POIs ou referências centrais.

## Decisions

### 1. Extensão de Assinatura e Estado no WidgetEditorMapas
- **Decisão**: Adicionar os atributos `self.e_idx: Optional[int] = -1` e `self.tipo: Optional[str] = None` em `WidgetEditorMapas`. Atualizar `set_mapa_atual` para receber `e_idx: Optional[int] = -1` e `tipo: str = 'setor'`.
- **Alternativa considerada**: Concatenar tudo em uma única string de ID. Rejeitada para evitar overhead de parsing e manter conformidade com a convenção de índices numéricos já adotada nos testes existentes.

### 2. Casamento Estrito em `selecionar_mapa_por_indices`
- **Decisão**: Expandir a assinatura para:
  ```python
  def selecionar_mapa_por_indices(
      self,
      pico_idx: Optional[int] = None,
      grupo_idx: Optional[int] = None,
      mapa_idx: Optional[int] = None,
      s_idx: Optional[int] = -1,
      e_idx: Optional[int] = -1,
      tipo: Optional[str] = None
  ) -> bool:
  ```
  O método verificará primeiro o `tipo` fornecido contra `dados[0]`. Se o `tipo` for omitido, deduzirá entre escalada, subsetor, grupo ou setor através da presença de `e_idx >= 0` e `s_idx >= 0`, preservando 100% de compatibilidade com chamadas legado.
- **Alternativa considerada**: Criar um novo método `selecionar_mapa_por_tupla`. Rejeitada pois diversas integrações chamam `selecionar_mapa_por_indices`; enriquecer a função existente mantém a interface simples e unificada (Princípio VI - Simplicidade).

### 3. Rolagem Automática (`scrollToItem`)
- **Decisão**: Sempre que `selecionar_mapa_por_indices` ou a restauração de seleção encontrar e definir o item via `setCurrentItem(item)`, invocar imediatamente `self.list_widget.scrollToItem(item)`.
- **Justificativa**: `setCurrentItem` com sinais bloqueados não garante scroll visível em todos os cenários de layout Qt. Chamar `scrollToItem` explícito resolve completamente o requisito de visibilidade.

### 4. Roteamento de Foco Global em `area_principal.py`
- **Decisão**: Atualizar `_on_foco_requisitado` para:
  1. Avaliar regexes de escalada ANTES dos regexes gerais de setor:
     - Sub-setor com escalada: `expando:setores/item:(\d+).*?expando:escaladas/item:(\d+).*?expando:mapas/item:(\d+)`
     - Setor com escalada: `expando:escaladas/item:(\d+).*?expando:mapas/item:(\d+)`
  2. Extrair `e_idx` e repassá-lo na chamada `editor.selecionar_mapa_por_indices(p_idx, sg_idx, m_idx, s_idx=s_idx, e_idx=e_idx, tipo=tipo)`.
  3. Expandir a busca por `ctx.arquivo_mapa` para também iterar sobre `escalada.mapas`.

### 5. URI de Contexto de Histórico
- **Decisão**: Em `set_mapa_atual`, gerar a URI de contexto apropriada para escaladas:
  - `page:mapas/node:Croqui/expando:picos/item:{p_idx}/expando:setores_ou_grupos/item:{sg_idx}/expando:setor/expando:escaladas/item:{e_idx}/expando:mapas/item:{m_idx}`
  Isso garante que ao dar Undo/Redo em ações realizadas em mapas de escalada, o foco retorne precisamente ao mapa da escalada.

## Risks / Trade-offs

- **[Risco] Chamadas legadas de testes chamando `selecionar_mapa_por_indices` com 3 ou 4 argumentos posicionais**
  - *Mitigação*: Manter a ordem original dos 4 primeiros parâmetros (`pico_idx, grupo_idx, mapa_idx, s_idx`) com valores padrão, adicionando `e_idx` e `tipo` como parâmetros opcionais com defaults compatíveis.
- **[Risco] Recursão de eventos Qt ao selecionar itens na lista**
  - *Mitigação*: Manter o padrão seguro de `self.list_widget.blockSignals(True)` durante a sincronização disparada internamente pelo `_renderizar_mapa`, checando se o item atual já é o correspondente antes de executar mutações desnecessárias.
