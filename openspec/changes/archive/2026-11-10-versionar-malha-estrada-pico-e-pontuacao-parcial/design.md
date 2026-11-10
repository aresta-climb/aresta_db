# Design

## Context

Veja `proposal.md`. O objetivo é versionar cada `MalhaEstradaPico` (`malha_estrada.yaml`) com `int32 versao = 4` no Protobuf e `VERSAO_ATUAL_MALHA_ESTRADA = 2` no código Python, diferenciando três estados:
1. **Ausente / Coordenada Divergente / Sem `duracao_minutos`**: `0/1000` pts (`concluida = False`), não exporta para `catalogo.db`, card de localização alerta que não foi gerado (ou que está sem tempo em minutos).
2. **Sincronizada, mas Versão Antiga (`versao < 2`)**: `700/1000` pts (`concluida = False`, ação `"Atualizar mapa de pontos"`), continua exportando para `catalogo.db` (para não quebrar o app enquanto não for regerada), card de localização alerta `⚠️ Mapa de pontos de estrada desatualizado (v<versao> → v2). Clique em Gerar Mapa de Pontos para atualizar.`.
3. **Atualizada (`versao >= 2`)**: `1000/1000` pts (`concluida = True`), exporta para `catalogo.db`, card de localização exibe `✅ Mapa de pontos de estrada gerado (<N> nós, v2).`.

## Goals / Non-Goals

**Goals:**
- Adicionar `int32 versao = 4;` em `MalhaEstradaPico` (`aresta_api/proto/croqui.proto`) e regenerar os stubs Protobuf.
- Definir `VERSAO_ATUAL_MALHA_ESTRADA = 2` em `scripts/gerar_malha_estrada_lib.py`, gravá-la em `construir_malha_estrada_pico_proto` e expor `malha_estrada_pico_sincronizada(pico)`, `obter_versao_malha_estrada_pico(pico)` e `malha_estrada_pico_atualizada(pico)`.
- Em `editor/core/avaliador_nota_qualidade.py`, atribuir `0.7` (`700` pts em pico único) e `concluida = False` para picos com malha sincronizada porém `versao < 2`, emitindo a ação `"Atualizar mapa de pontos"`.
- Em `editor/views/widget_mensagem_coordenada.py`, exibir o aviso de versão desatualizada (`v<atual> → v2`) no rótulo de status do card de localização.

**Non-Goals:**
- Alterar o esquema SQLite (`catalogo.sql`) ou o app Flutter (a versão é metadado de curadoria/compilação em `MalhaEstradaPico`).

## Decisions

### 1. Separação entre `malha_estrada_pico_sincronizada` e `malha_estrada_pico_atualizada`
- **Decisão**:
  - `malha_estrada_pico_sincronizada(pico: Any) -> bool`: valida localização não-zero, `nos` não-vazio, coordenadas de referência iguais à localização do pico e `duracao_minutos > 0` para todo nó com `distancia_metros > 0`. É usada por `extrair_linhas_malha_de_pico_proto` para que croquis com `versao < 2` continuem populando `catalogo.db` até serem atualizados.
  - `obter_versao_malha_estrada_pico(pico: Any) -> int`: retorna `int(malha.get("versao", 0) or 0)` (dict) ou `int(malha.versao or 0)` (Protobuf).
  - `malha_estrada_pico_atualizada(pico: Any) -> bool`: retorna `malha_estrada_pico_sincronizada(pico) and obter_versao_malha_estrada_pico(pico) >= VERSAO_ATUAL_MALHA_ESTRADA`.

### 2. Cálculo de Pontuação Parcial (`700/1000`) em `avaliador_nota_qualidade.py`
- **Decisão**:
  - Criar `_avaliar_estado_malha_estrada_pico(pico, croqui_path, cache_md) -> str` retornando `"atualizada"`, `"versao_antiga"` ou `"ausente"`.
  - Para cada pico:
    - `"atualizada"` soma `1.0` em `unidades_malha` e `1` em `picos_atualizados`;
    - `"versao_antiga"` soma `0.7` em `unidades_malha`, não incrementa `picos_atualizados` e adiciona a ação `AcaoTarefaQualidade(f"Atualizar mapa de pontos{sufixo_p}", uri_loc)`;
    - `"ausente"` soma `0.0` e adiciona `"Gerar mapa de pontos"` (ou `"Adicionar localização"`).
  - `pts_malha = int(round(1000 * (unidades_malha / len(picos_raw))))` (quando `tem_picos`), e `conc_malha = tem_picos and (picos_atualizados == len(picos_raw))`.
