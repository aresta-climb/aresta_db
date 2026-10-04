# Spec Delta: mapa-referencias-centralizadas

## MODIFIED Requirements

### Requirement: Centralização das Referências no Mapa
O sistema SHALL agrupar todas as referências de escalada/pontos de interesse no próprio objeto `Mapa` usando a estrutura `Referencia`, e não nas entidades (`Boulder`, `ViaEsportiva`, `Setor`, etc.). As referências passam a apontar primariamente para o ID da entidade folha através do campo `alvo_id`, enquanto os campos de texto `escalada`, `setor` e `grupo` são marcados como deprecados e mantidos apenas para preenchimento de compatibilidade retroativa. Além disso, deve haver uma validação estrita, exigindo que as IDs referenciadas existam nos pontos de interesse mapeados no frontmatter do mapa correspondente.

#### Scenario: Leitura de Referência Genérica com alvo_id
- **WHEN** o sistema processa um `Mapa`
- **THEN** ele lê a lista de `referencias` utilizando o campo `alvo_id` para identificar diretamente a entidade correspondente em tempo O(1)

#### Scenario: Validação Estrita de Existência
- **WHEN** o sistema valida uma referência no mapa
- **THEN** ele verifica de forma estrita se os IDs referenciados existem nos pontos de interesse do SVG ou frontmatter, rejeitando correspondências parciais ou inválidas

### Requirement: Escopo Implícito e Explícito de Referências
O sistema SHALL priorizar a resolução de referências através do campo `alvo_id`. Caso `alvo_id` seja zero ou não fornecido (compatibilidade com croquis não migrados), o sistema SHALL recorrer à resolução legada por strings, assumindo que uma `Referencia` apontando para `escalada` (sem definir `setor` ou `grupo`) pertence ao Setor em que o `Mapa` está aninhado.

#### Scenario: Resolução Primária por alvo_id
- **WHEN** a referência possui `alvo_id` maior que zero
- **THEN** o sistema resolve a referência diretamente para a entidade com aquele ID, independentemente de sua posição na hierarquia de setores ou grupos

#### Scenario: Fallback para Referência Legada em Mapa de Setor
- **WHEN** a referência não possui `alvo_id`, mas possui `escalada` preenchida e está dentro do YAML de um Setor
- **THEN** o sistema resolve a referência para a escalada daquele setor com o nome exato

#### Scenario: Fallback para Referência Legada em Mapa de Grupo
- **WHEN** a referência não possui `alvo_id` e está na raiz de um Grupo tentando referenciar uma escalada sem prover o campo `setor`
- **THEN** o validador do YAML/deploy SHALL emitir um warning indicando que a referência é ambígua

## ADDED Requirements

### Requirement: Retrocompatibilidade de Strings no Compilado
O compilador de croquis SHALL preencher automaticamente os campos deprecados `escalada`, `setor` e `grupo` no `compilado.binarypb` a partir do `alvo_id` da referência, garantindo que versões legadas de clientes continuem funcionando sem alterações.

#### Scenario: Exportação para Formato Compilado
- **WHEN** o compilador gera o `compilado.binarypb` para um croqui com referências que utilizam `alvo_id`
- **THEN** ele insere os nomes textuais correspondentes nos campos `escalada`, `setor` e `grupo` da mensagem `Referencia`
