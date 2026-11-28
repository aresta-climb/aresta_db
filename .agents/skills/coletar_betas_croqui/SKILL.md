---
name: coletar_betas_croqui
description: Executa e monitora a coleta multi-fonte de candidatos a beta do croqui aberto no Editor Aresta 100% via MCP usando aresta_coletar_betas, suportando desde setores isolados até croquis de 1.000+ vias sem bloquear a UI.
---

# Coleta Multi-Fonte de Betas (100% via MCP `editor-aresta`)

Sua missão é acionar e acompanhar a coleta automatizada de candidatos a beta (YouTube via `InnerTube`, além de Instagram, TikTok, Facebook, Twitter/X, Reddit, portais UGC e Blogs via `ddgs` com extração de vídeos embutidos em blogs aprovados) diretamente no **Editor Aresta** via servidor MCP **`editor-aresta`** através da ferramenta `aresta_coletar_betas`.

> [!IMPORTANT]
> **Arquitetura Não-Bloqueante, Incremental e com Reavaliação Offline:**
> - Antes de disparar requisições na rede, `aresta_coletar_betas` reavalia offline itens em `betas_rejeitados` marcados com `[Query: ... | Auto-filtrado: ...]` usando as regras mais recentes de filtro e contexto geográfico (`Pico.cidade` + `Croqui.nome`), promovendo os recém-aprovados em `auto_filtrados_promovidos` sem refazer scraping nem tocar em rejeições humanas.
> - Vias com nome placeholder (`Sem nome \d*`, `Projeto \d*`) são ignoradas sem requisições de rede.
> - A ferramenta `aresta_coletar_betas` roda **fora da thread principal do Qt** em um pool de threads em background e aplica micro-lotes (`tamanho_lote_flush`, padrão 10 vias) incrementalmente no `CroquiController` (preservando Undo/Redo).
> - Se a coleta for longa ou cancelada no meio, todo o progresso dos micro-lotes já concluídos permanece salvo em memória em `curadoria_betas.conteudo`.
> - Por padrão (`apenas_sem_coleta=True`), escaladas que já possuem candidatos/rejeitados em `curadoria_betas` ou betas publicados em `Escalada.betas` são ignoradas na busca web (passando `apenas_sem_coleta=False`, novas buscas descobrem vídeos novos mantendo todos os rejeitados anteriores descartados).

---

## 1. Verificação Inicial do Croqui (`id_croqui`)

1. Chame `aresta_listar_croquis()` para identificar os croquis em `abertos`. Se houver mais de um croqui aberto (ou se o usuário informou `id_croqui`), propague `id_croqui="<id_croqui>"` em **todas** as chamadas ao `editor-aresta` (`aresta_status_workspace`, `aresta_listar_escaladas`, `aresta_coletar_betas`, `aresta_listar_betas_nao_scorados`, `aresta_adicionar_betas_revisao`).
2. Chame `aresta_status_workspace(id_croqui="<id_croqui>")` para confirmar o croqui ativo.
3. Caso o usuário queira coletar apenas um setor específico ou algumas vias, utilize `aresta_listar_escaladas(id_croqui="<id_croqui>")` (ou filtre pelo nome/UID do setor em `alvo_setor`).
4. Para inserir manualmente links avulsos encontrados fora da coleta automática diretamente na fila de curadoria humana, utilize `aresta_adicionar_betas_revisao(id_croqui="<id_croqui>", itens=[...])`.

---

## 2. Disparo da Coleta (`aresta_coletar_betas`)

Invoque `aresta_coletar_betas` no MCP `editor-aresta` com `acao="iniciar"`:

```json
{
  "id_croqui": "<id_croqui>",
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
  - `auto_filtrados_promovidos` (resgatados offline de `betas_rejeitados`)
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
