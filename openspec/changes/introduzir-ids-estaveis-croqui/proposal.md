# Proposal: Introduzir IDs Estáveis para Croquis e Entidades

## Why

Atualmente, o ecossistema Aresta Climb referencia escaladas, setores e grupos por meio de cadeias textuais de nomes (strings) e slugs em toda a hierarquia de mapas, rotas e navegação. Esse acoplamento textual gera fragilidade considerável: renomear uma via ou alterar sua estrutura exige caçar e reescrever referências em múltiplos arquivos e mapas, além de introduzir complexidade desnecessária nos clientes de consumo.

Além disso, a nova arquitetura de persistência e comunidade (integrando sincronização de cadernetas via PowerSync, banco relacional Supabase e placas físicas de aço inoxidável gravadas a laser nas falésias) exige identificadores numéricos inteiros de 4 bytes imutáveis em 2 níveis (`croqui_id` global estável e `escalada_id` único por croqui). Para que uma placa de inox como `app.arestaclimb.com/12/35` funcione por 30 anos sem risco de quebra, os identificadores precisam ser nativos, garantidos pelo compilador, atribuídos deterministicamente e usados diretamente pelas referências visuais de mapas.

## What Changes

- **Modelagem Protobuf em `indice.proto`**:
  - Adição do campo invisível `int32 proximo_id = 3 [(aresta.formato_na_ui) = INVISIVEL]` em `Indice`.
  - Adição do campo invisível `int32 id_numerico = 12 [(aresta.formato_na_ui) = INVISIVEL]` em `ResumoCroqui`.
- **Modelagem Protobuf em `croqui.proto`**:
  - Adição dos campos invisíveis `int32 id_numerico = 17` e `int32 proximo_id = 18` em `Croqui`.
  - Adição do campo invisível `int32 id = 10` em `Grupo`.
  - Adição do campo invisível `int32 id = 16` em `Setor`.
  - Adição do campo invisível `int32 id = 8` na mensagem unificada `Escalada`.
  - Adição de `int32 alvo_id = 7` em `Mapa.Referencia` apontando diretamente para o ID folha único da entidade referenciada (Escalada, Setor ou Grupo).
  - Marcação de `string escalada = 4`, `string setor = 3` e `string grupo = 2` como `[deprecated = true]` em `Mapa.Referencia`.
- **Geração e Ciclo de Vida de IDs no Editor**:
  - Atribuição automática de `id` para qualquer nova Escalada, Setor ou Grupo criado no editor, consumindo e incrementando `croqui.proximo_id`.
  - Garantia de monotonicidade estrita: o contador `proximo_id` nunca decrementa em operações de Undo (Desfazer), evitando colisões ou reciclagem de identificadores.
  - O editor de mapas passa a gravar primariamente `alvo_id` nas novas referências e preenche os campos legados para retrocompatibilidade.
- **Compilador e Guardião de Integridade (`deploy_generated.py` e `preparar_submissao_lib.py`)**:
  - Atribuição automática de `id_numerico` para croquis não numerados a partir do `proximo_id` do índice.
  - Detecção e atribuição automática de `id` para qualquer entidade sem ID ou criada via edição manual no Markdown.
  - Preenchimento automático dos campos de compatibilidade retroativa (`escalada`, `setor`, `grupo`) durante a compilação.
- **Migração Inicial do Acervo Existente (`migracoes/0005_atribuir_ids_estaveis.py`)**:
  - Atribuição determinística (ordem alfabética dos slugs) de IDs para todos os croquis existentes (1 a N).
  - Atribuição in-place de IDs para todos os grupos, setores e escaladas no `database/`.
  - Migração de todas as `referencias` de mapas para conter o `alvo_id` correspondente.

## Capabilities

### New Capabilities
- `identificadores-estaveis`: Governa a geração, persistência in-place no Git, integridade no compilador e resolução em tempo O(1) de identificadores numéricos estáveis em 2 níveis (`croqui_id` global e IDs unificados de entidades por croqui).

### Modified Capabilities
- `mapa-referencias-centralizadas`: Atualiza os requisitos de referência em mapas para priorizar a ligação direta via `alvo_id` da entidade folha, mantendo resolução retrocompatível com as strings legadas.

## Impact

- **Protobufs**: Recompilação dos stubs Python gerados (`croqui_pb2.py`, `indice_pb2.py`).
- **Banco de Dados Git (`database/`)**: Migração in-place adicionando `id_numerico` e `proximo_id` nos `croqui.yaml`, `id` no frontmatter de arquivos `.md` e `alvo_id` nas referências de mapas.
- **Compilador e Deploy**: `deploy_generated.py` e `preparar_submissao_lib.py` atualizados para auditar, sincronizar e manter os contadores de ID.
- **Editor Desktop**: Controladores de criação de entidades atualizados para injetar `id` via `croqui.proximo_id`.
- **Compatibilidade**: 100% retrocompatível; versões legadas do `aresta_app` continuam lendo `compilado.binarypb` com os campos de texto preenchidos automaticamente.
