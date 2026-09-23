## Context

Ver `proposal.md` para motivação e descrição do problema.
Atualmente, no método `adicionar_rota_com_tracado` de `editor/controllers/mapas_controller.py`, cada ponto do trajeto desenhado é verificado contra nós existentes através de `detectar_snap_nos`. Quando múltiplos cliques ocorrem no mesmo ponto (ou via duplo clique para finalizar a linha), a lista `indices_no_cand` armazena índices repetidos (ex: `[1, 1]`). A condição anterior checava apenas `len >= 2` e os elementos extremos da lista, fazendo com que `idx_in = min(...)` e `idx_out = max(...)` fossem iguais, disparando `fatiar_linha_triplo` com índices inválidos e quebrando a execução.

## Goals / Non-Goals

**Goals:**
- Garantir que `fatiar_linha_triplo` seja invocado única e exclusivamente quando existirem pelo menos dois nós intermediários distintos (`0 < idx_in < idx_out < total_nos - 1`).
- Validar a coerência de direção e ordenação temporal do trajeto (`pos_in < pos_out`).
- Implementar fallback resiliente em `adicionar_rota_com_tracado` para que qualquer falha geométrica reverta para adição de linha independente (caso simples), sem estourar exceção para o usuário.
- Sanitizar pontos consecutivos duplicados no `widget_editor_mapas.py` ao concluir o traçado via duplo clique.
- Endurecer as validações de limites em `topologia_trajeto.py: fatiar_linha_triplo`.
- Manter 100% de cobertura de testes unitários conforme os princípios do repositório (`AGENTS.md`).

**Non-Goals:**
- Suportar reversão topológica automática de nós em travessias desenhadas em sentido contrário ao da linha base (caso ocorra sentido inverso, o fallback adiciona a linha de forma independente sem corromper as geometrias).
- Alterar o comportamento de bifurcações compartilhadas na base (`snap_inicio.indice_no == 0`).

## Decisions

### Decisão 1: Validação de nós únicos e estritamente intermediários no Controller
- **Abordagem**: Extrair `nos_unicos = sorted(set(indices_no_cand))` e verificar:
  ```python
  if len(nos_unicos) >= 2 and nos_unicos[0] > 0 and nos_unicos[-1] < len(linha_cand.linha.conteudo.nos) - 1:
      idx_in = nos_unicos[0]
      idx_out = nos_unicos[-1]
  ```
  Além disso, certificar que `pos_in < pos_out`.
- **Racional**: Uma travessia de segmento compartilhado requer que a linha seja percorrida entre dois nós distintos. Se houver apenas 1 nó único, trata-se de um ponto de toque/junção, e não de um trecho de travessia.
- **Alternativas consideradas**: Permitir fatiamento com 1 nó. Rejeitado, pois fatiar em 1 nó cria apenas 2 sublinhas (`fatiar_linha_em_no`), enquanto `fatiar_linha_triplo` geraria sublinhas degeneradas com 1 nó só.

### Decisão 2: Fallback gracioso com bloco `try/except` na adição de rotas
- **Abordagem**: Envolver as rotinas de fatiamento topológico em `adicionar_rota_com_tracado` em blocos de captura de `Exception` (ou especificamente `ValueError`), registrando aviso em log e deixando a flag `fatiou = False`.
- **Racional**: Erros topológicos durante o desenho não devem travar a aplicação nem degradar a experiência do usuário no editor. Caso a topologia não consiga ser fatiada com segurança, a rota é criada como um traçado avulso no setor.
- **Alternativas consideradas**: Deixar a exceção propagar. Rejeitado, pois gera erros não tratados no Sentry e fecha/trava a janela do editor.

### Decisão 3: Sanitização de pontos idênticos consecutivos na View
- **Abordagem**: Em `WidgetEditorMapas.finalizar_modo_nova_rota()`, filtrar `self.pontos_nova_rota` removendo pontos consecutivos com distância zero ou $< 1.0\text{ px}$.
- **Racional**: O evento `mouseDoubleClickEvent` no Qt é precedido por um `mousePressEvent`, inserindo naturalmente um ponto redundante no mesmo local do clique final. A higienização evita trechos com comprimento nulo e previne o envio de múltiplos nós sobrepostos ao controlador.
- **Alternativas consideradas**: Descartar incondicionalmente o último ponto em `mouseDoubleClickEvent`. Rejeitado, pois se o usuário iniciar e der duplo clique para fazer uma reta de 2 pontos, o segundo ponto seria incorretamente perdido.

### Decisão 4: Endurecimento do contrato de `fatiar_linha_triplo` no Core
- **Abordagem**: Atualizar a condição de validação de `fatiar_linha_triplo` para `0 < indice_entrada < indice_saida < total_nos - 1`.
- **Racional**: Linhas com apenas 1 nó são inválidas na representação vetorial do Aresta. Para que as três sublinhas resultantes (`0..in`, `in..out`, `out..N-1`) tenham no mínimo 2 nós cada, os índices de entrada e saída precisam ser estritamente internos.

## Risks / Trade-offs

- **[Risco] Traçados desenhados no sentido reverso não realizam fatiamento triplo**:
  - *Mitigação*: O fallback adiciona a rota como linha independente sem corromper os IDs das vias existentes, garantindo estabilidade e integridade dos dados.
- **[Risco] Filtragem de pontos na View descartar nós intencionais muito próximos**:
  - *Mitigação*: A tolerância é restrita a nós estritamente coincidentes ou com distância mínima inferior a 1 pixel, afetando apenas cliques repetidos no mesmo local.
