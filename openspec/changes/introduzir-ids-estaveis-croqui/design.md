# Technical Design: Introduzir IDs Estáveis para Croquis e Entidades

## Context

O Aresta Climb utiliza Protobuf Edition 2023 (`croqui.proto` e `indice.proto`) para serialização de croquis e catálogos. O armazenamento-fonte no Git (`database/`) utiliza arquivos YAML (`croqui.yaml`) e Markdown com YAML Frontmatter (`grupo_*.md`, `setor_*.md`).

Historicamente, as conexões entre mapas visuais e dados eram mantidas através de triplas textuais `(grupo, setor, escalada)` em `Mapa.Referencia`. Com a introdução da arquitetura de sincronização offline-first (PowerSync + Supabase) e links físicos permanentes (placas de aço inox na rocha), há a necessidade imperativa de identificadores numéricos inteiros (`int32`) em dois níveis hierárquicos:
1. **Nível 1 (Global)**: `croqui_id` estável no índice.
2. **Nível 2 (Local)**: `escalada_id` único no escopo de cada croqui.

Ver `proposal.md` para motivação e `specs/` para os requisitos contratuais.

## Goals / Non-Goals

**Goals:**
- Estabelecer espaço numérico de 4 bytes (`int32`) para cada croqui no índice global via `indice.proximo_id`.
- Estabelecer espaço numérico unificado por croqui via `croqui.proximo_id`, compartilhado entre Grupos, Setores e Escaladas.
- Desacoplar referências em mapas, adotando o campo folha único `alvo_id` em `Mapa.Referencia`.
- Implementar abordagem híbrida de geração de IDs (geração imediata no Editor e auditoria/atribuição como guardião no compilador).
- Garantir monotonicidade estrita de `proximo_id` no histórico (não decrementar no Undo).
- Assegurar 100% de compatibilidade retroativa com clientes e pipelines existentes, preenchendo automaticamente strings legadas durante a compilação.
- Fornecer lookup reativo $O(1)$ de entidades por ID (`Map<int, ResolucaoEntidade>`).

**Non-Goals:**
- Não criar contador ou identificador separado para `Pico`: adota-se a relação estrita 1:1 onde `croqui_id == pico_id`.
- Não remover imediatamente as strings `escalada`, `setor`, `grupo` dos protobufs gerados (mantê-las marcadas como `deprecated` para compatibilidade).
- Não alterar a sintaxe ou coordenadas vetoriais de POIs nos mapas.

## Decisions

### 1. Modelagem Protobuf nos Arquivos de Contrato

#### A. `aresta_api/proto/indice.proto`
- Em `Indice`:
  ```protobuf
  int32 proximo_id = 3 [(aresta.formato_na_ui) = INVISIVEL];
  ```
- Em `ResumoCroqui`:
  ```protobuf
  int32 id_numerico = 12 [(aresta.formato_na_ui) = INVISIVEL];
  ```

#### B. `aresta_api/proto/croqui.proto`
- Em `Croqui`:
  ```protobuf
  int32 id_numerico = 17 [(aresta.formato_na_ui) = INVISIVEL];
  int32 proximo_id = 18 [(aresta.formato_na_ui) = INVISIVEL];
  ```
- Em `Grupo`:
  ```protobuf
  int32 id = 10 [(aresta.formato_na_ui) = INVISIVEL];
  ```
- Em `Setor`:
  ```protobuf
  int32 id = 16 [(aresta.formato_na_ui) = INVISIVEL];
  ```
- Em `Escalada`:
  ```protobuf
  int32 id = 8 [(aresta.formato_na_ui) = INVISIVEL];
  ```
- Em `Mapa.Referencia`:
  ```protobuf
  int32 alvo_id = 7;
  string grupo = 2 [deprecated = true];
  string setor = 3 [deprecated = true];
  string escalada = 4 [deprecated = true];
  ```

*Alternativa considerada*: Colocar o `id` dentro de cada sub-mensagem de escalada (`ViaEsportiva`, `Boulder`, etc.). Rejeitada por gerar duplicação em 5 mensagens filhas quando `Escalada` já atua como envelope polimórfico comum.

### 2. Geração Híbrida de IDs (Editor + Compilador)

- **No Editor (`editor/controllers/croqui_controller.py`)**:
  - Ao invocar criação de uma nova escalada, setor ou grupo, o controlador lê `croqui.proximo_id`, injeta-o no objeto novo e incrementa `croqui.proximo_id += 1`.
  - Essa ação é encapsulada em comando na pilha de histórico (`QUndoCommand`).
- **No Compilador (`scripts/preparar_submissao_lib.py` e `deploy_generated.py`)**:
  - Atua como rede de segurança: caso um arquivo Markdown ou YAML seja editado manualmente fora do editor e inserido sem `id`, o compilador identifica `id is None`, atribui `croqui.proximo_id` e regrava o arquivo.
  - No índice, o `deploy_generated.py` garante que qualquer croqui recém-adicionado receba `indice.proximo_id`.

*Alternativa considerada*: Deixar a atribuição exclusivamente para a compilação. Rejeitada porque impediria desenhar e linkar traçados no Editor de Mapas imediatamente após criar uma nova via no rascunho.

### 3. Monotonicidade Estrita no Undo (Nunca Decrementar)

No método `undo()` dos comandos de criação de entidade:
- O objeto criado é removido da lista (`escaladas`, `setores` ou `setores_ou_grupos`).
- O contador `croqui.proximo_id` **não é decrementado**.
- *Justificativa*: Segue o padrão de sequences relacionais. Evita reutilização de identificadores que já possam ter sido propagados para referências de mapa, buffers de sincronização local do PowerSync ou logs temporários. Gaps numéricos em chaves primárias são inofensivos.

### 4. Referenciamento por Leaf ID (`alvo_id`) e Compatibilidade

- Como o espaço numérico de `proximo_id` é único por croqui, nenhum Grupo, Setor ou Escalada compartilha o mesmo número.
- O campo `alvo_id` em `Mapa.Referencia` armazena exclusivamente o ID da entidade folha desenhada.
- **Sincronização no Deploy**: A rotina de compilação em `scripts/preparar_submissao_lib.py` resolve o `alvo_id`, identifica o nome da entidade e seus ancestrais e preenche os campos legados `escalada`, `setor` e `grupo` no `.binarypb` final.

```text
       Mapa.Referencia no Git (MD/YAML)
       +-------------------------------+
       | alvo_id: 35                   |
       +-------------------------------+
                       |
                       v [ Compilação / deploy_generated ]
       Mapa.Referencia no compilado.binarypb
       +-------------------------------+
       | alvo_id: 35                   |
       | escalada: "Deslize" (legado)  |
       | setor: "Bloco Deslize" (leg.) |
       | grupo: "Deslize" (legado)     |
       +-------------------------------+
```

### 5. Resolução O(1) Reativa em Memória

No `aresta_app` e no `editor`:
- Implementa-se uma estrutura de indexação construída no carregamento do croqui:
  ```dart
  class ResolucaoEntidade {
    final dynamic entidade; // Escalada, Setor ou Grupo
    final Setor? setorPai;
    final Grupo? grupoPai;
  }
  final Map<int, ResolucaoEntidade> indiceLookup;
  ```
- Sempre que o croqui for recarregado ou atualizado via Live Reload / Hot Reload, `indiceLookup` é invalidado e reconstruído de forma reativa.

## Risks / Trade-offs

| Risco Identificado | Severidade | Mitigação |
| :--- | :--- | :--- |
| **Colisão de `proximo_id` em merges concorrentes no Git** | Média | O guardião em `corrigir_database()` detecta duplicatas numéricas e reatribui IDs determinística e monotonicamente, atualizando referências de mapas. |
| **Clientes antigos quebrando por ausência de nomes** | Alta | O compilador garante que `compilado.binarypb` continue povoado com todas as strings legadas (`escalada`, `setor`, `grupo`). |
| **Gaps numéricos causados por Undo ou remoções** | Baixa | Nenhuma mitigação necessária. IDs são identificadores opacos de máquina com capacidade para 2,1 bilhões de registros por croqui. |

## Migration Plan

1. **Recompilação de Protobufs**: Executar `python build.py` gerando os novos stubs `croqui_pb2.py` e `indice_pb2.py`.
2. **Migração Sequencial 0005 (`migracoes/0005_atribuir_ids_estaveis.py`)**:
   - Ordenar todos os croquis alfabeticamente por slug e atribuir `id_numerico = 1..N` no `indice.yaml`.
   - Para cada croqui, inicializar `proximo_id = 1` e varrer `picos -> setores_ou_grupos -> setores -> escaladas`, gravando `id` em cada entidade no frontmatter dos arquivos `.md` e no `croqui.yaml`.
   - Varrer todos os mapas e preencher `alvo_id` nas `referencias` cruzando com os nomes existentes.
3. **Atualização do Compilador e Editor**:
   - Atualizar `deploy_generated.py`, `preparar_submissao_lib.py` e controladores do editor.
4. **Validação**:
   - Executar suíte de testes com 100% de cobertura e compilar o acervo completo verificando integridade de dados e geração do índice.
