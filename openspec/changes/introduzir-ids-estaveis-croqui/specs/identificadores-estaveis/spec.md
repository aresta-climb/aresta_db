# Spec Delta: identificadores-estaveis

## Purpose

Garante a integridade referencial física e digital permanente através de identificadores numéricos inteiros estáveis em dois níveis: croqui global e entidades unificadas locais.

## ADDED Requirements

### Requirement: Espaço Numérico Global de Croquis no Índice
O sistema SHALL atribuir e manter um identificador numérico estável `id_numerico` (inteiro de 4 bytes) para cada croqui registrado no índice, gerido por um contador sequencial `proximo_id` no objeto `Indice`.

#### Scenario: Atribuição de ID a Novo Croqui no Índice
- **WHEN** o `deploy_generated` processa um croqui que ainda não possui `id_numerico` no índice
- **THEN** o sistema atribui o valor atual de `indice.proximo_id`, incrementa o contador e persiste o valor no `indice.yaml` e no `croqui.yaml` correspondente

#### Scenario: Preservação Estrita de ID Existente
- **WHEN** o sistema processa um croqui que já possui `id_numerico` atribuído
- **THEN** o sistema preserva o valor inalterado, garantindo imutabilidade referencial perpétua

### Requirement: Espaço Numérico Unificado Local por Croqui
O sistema SHALL manter um contador sequencial `proximo_id` no objeto `Croqui` compartilhado de forma unificada entre Grupos, Setores e Escaladas, garantindo unicidade de IDs no escopo do croqui.

#### Scenario: Criação de Entidade no Editor
- **WHEN** o usuário cria uma nova Escalada, Setor ou Grupo através da interface do editor
- **THEN** o sistema atribui o valor atual de `croqui.proximo_id` ao campo `id` da entidade e incrementa `croqui.proximo_id` via comando na pilha de histórico

#### Scenario: Monotonicidade Estrita no Undo
- **WHEN** o usuário desfaz (Undo/Ctrl+Z) a criação de uma entidade no editor
- **THEN** a entidade criada é removida, mas o contador `croqui.proximo_id` não é decrementado, prevenindo reciclagem ou colisão de identificadores

#### Scenario: Atribuição pelo Compilador a Entidades Manuais
- **WHEN** o compilador (`corrigir_database`) encontra uma entidade em arquivo `.md` sem campo `id`
- **THEN** o sistema atribui o valor de `croqui.proximo_id`, incrementa o contador e regrava o arquivo no disco

### Requirement: Ocultação de Campos de Identificação no Editor
Os campos `id_numerico`, `id` e `proximo_id` SHALL ser marcados com a extensão Protobuf `[(aresta.formato_na_ui) = INVISIVEL]`, não sendo exibidos nos formulários de edição do editor.

#### Scenario: Exibição de Formulário
- **WHEN** o editor renderiza os formulários de dados de Croqui, Grupo, Setor ou Escalada
- **THEN** os campos `id`, `id_numerico` e `proximo_id` não aparecem para o usuário

### Requirement: Resolução O(1) Reativa de Entidades por ID
O sistema SHALL disponibilizar uma tabela indexada em memória que permita resolver em tempo O(1) qualquer entidade (Escalada, Setor ou Grupo) e seus ancestrais pelo seu ID numérico, atualizada reativamente a cada mutação do croqui.

#### Scenario: Consulta Direta por ID de Escalada
- **WHEN** o sistema recebe uma consulta por um ID de escalada válido
- **THEN** ele retorna instantaneamente o objeto da escalada, seu setor pai e seu grupo pai sem realizar varredura linear

#### Scenario: Invalidação e Atualização Reativa
- **WHEN** o objeto `Croqui` sofre qualquer alteração ou recarregamento
- **THEN** a tabela de lookup por ID é imediatamente reconstruída refletindo o estado atualizado
