---
name: coletar_betas_croqui
description: Executa e monitora a coleta multi-fonte de candidatos a beta do croqui aberto no Editor Aresta 100% via MCP usando aresta_coletar_betas, suportando desde setores isolados até croquis de 1.000+ vias sem bloquear a UI.
---

# Coleta Multi-Fonte de Betas (100% via MCP)

Sua missão é acionar e acompanhar a coleta automatizada de candidatos a beta (YouTube, Instagram, TikTok, Facebook, Twitter/X, Reddit, portais UGC e Blogs) diretamente no **Editor Aresta** via MCP através da ferramenta `aresta_coletar_betas`.

> [!IMPORTANT]
> **Arquitetura Não-Bloqueante e Incremental:**
> - A ferramenta `aresta_coletar_betas` roda **fora da thread principal do Qt** em um pool de threads em background e aplica micro-lotes (`tamanho_lote_flush`, padrão 10 vias) incrementalmente no `CroquiController` (preservando Undo/Redo).
> - Se a coleta for longa ou cancelada no meio, todo o progresso dos micro-lotes já concluídos permanece salvo em memória em `curadoria_betas.conteudo`.
> - Por padrão (`apenas_sem_coleta=True`), escaladas que já possuem candidatos/rejeitados em `curadoria_betas` ou betas publicados em `Escalada.betas` são automaticamente ignoradas, permitindo retomar coletas de croquis gigantes de onde pararam sem retrabalho.

---

## 1. Verificação Inicial do Croqui

1. Chame `aresta_status_workspace()` para confirmar que há um croqui aberto no Editor Aresta.
2. Caso o usuário queira coletar apenas um setor específico ou algumas vias, utilize `aresta_listar_escaladas()` (ou filtre pelo nome/UID do setor em `alvo_setor`).

---

## 2. Disparo da Coleta (`aresta_coletar_betas`)

Invoque `aresta_coletar_betas` com `acao="iniciar"`:

```json
{
  "acao": "iniciar",
  "alvo_setor": "",
  "apenas_sem_coleta": true,
  "aguardar_segundos": 15,
  "tamanho_lote_flush": 10
}
```

### Parâmetros Disponíveis
- `acao`: `"iniciar"` (padrão), `"status"` ou `"cancelar"`.
- `alvo_setor` *(opcional)*: UID ou nome exato do setor para restringir a coleta a um único setor.
- `escaladas_uids` *(opcional)*: Lista de UIDs de escaladas específicas para coletar.
- `apenas_sem_coleta` *(opcional, padrão `true`)*: Quando `true`, pula escaladas que já possuem entradas em `curadoria_betas` ou betas aprovados em `Escalada.betas`. Passe `false` apenas quando o usuário pedir explicitamente para re-coletar vias já processadas.
- `aguardar_segundos` *(opcional, `0` a `20`, padrão `15`)*: Tempo máximo de long-polling por chamada MCP antes de retornar o status parcial.
- `tamanho_lote_flush` *(opcional, padrão `10`)*: Quantidade de escaladas concluídas acumuladas antes de gravar um micro-lote no `CroquiController`.

---

## 3. Acompanhamento em Croquis Grandes (100 a 1.000+ Vias)

Examine o campo `status` retornado por `aresta_coletar_betas`:

- **`status == "concluido"`**:
  Todas as escaladas selecionadas foram processadas e gravadas em `curadoria_betas.conteudo`.
- **`status == "em_andamento"`**:
  A coleta continua rodando em background no Editor Aresta. O payload informa:
  - `total_escaladas`, `escaladas_processadas`, `escaladas_restantes`
  - `novos_candidatos_adicionados` (em `betas_nao_scorados`)
  - `novos_rejeitados_adicionados` (em `betas_rejeitados`)
  - `ultima_escalada`
  - `total_escaladas_com_nao_scorados` e `total_candidatos_nao_scorados`

### Como proceder enquanto `status == "em_andamento"`:
1. Chame `aresta_coletar_betas(acao="status", aguardar_segundos=15)` repetidamente até que `status` mude para `"concluido"`.
2. **Dica para croquis de 1.000+ vias**:
   - Como os micro-lotes são gravados incrementalmente a cada 10 vias, você pode inclusive consultar ou iniciar a avaliação de lotes já coletados via `aresta_listar_betas_nao_scorados(offset=0, limite=25)` ou aguardar a conclusão por setor (`alvo_setor`).
   - Se precisar interromper a qualquer momento a pedido do usuário, chame `aresta_coletar_betas(acao="cancelar")` — o progresso já coletado será preservado.

---

## 4. Encadeamento com Avaliação (`avaliar_betas_croqui`)

Ao concluir a coleta:
1. Informe ao usuário o resumo retornado (`escaladas_processadas`, `novos_candidatos_adicionados`, `novos_rejeitados_adicionados` e `total_candidatos_nao_scorados`).
2. Se houver candidatos pendentes (`total_candidatos_nao_scorados > 0`) e o usuário desejar avaliá-los na sequência, siga as instruções da skill `avaliar_betas_croqui` utilizando `aresta_listar_betas_nao_scorados` de forma paginada.
