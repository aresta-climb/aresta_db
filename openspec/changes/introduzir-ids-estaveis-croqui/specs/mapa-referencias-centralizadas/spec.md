# Spec Delta: mapa-referencias-centralizadas

## MODIFIED Requirements

### Requirement: Centralização das Referências no Mapa
O sistema SHALL agrupar todas as referências de escalada/pontos de interesse no próprio objeto `Mapa` usando a estrutura `Referencia`, e não nas entidades (`Boulder`, `ViaEsportiva`, `Setor`, etc.). No banco de dados fonte (`database/`) e no compilado, as referências passam a apontar exclusivamente para os UIDs descentralizados através dos campos `alvo_uid` e `pontos_uids`, eliminando a necessidade de declarar nomes textuais (`escalada`, `setor`, `grupo`) nos arquivos Markdown. Além disso, deve haver uma validação estrita, exigindo que os UIDs referenciados existam nos pontos de interesse mapeados no frontmatter do mapa correspondente.

#### Scenario: Leitura de Referência Genérica
- **WHEN** o sistema processa um `Mapa` nos arquivos fontes
- **THEN** ele lê a lista de `referencias` utilizando o campo `alvo_uid` para identificar a entidade folha e `pontos_uids` para a lista ordenada de pontos do traçado

#### Scenario: Validação Estrita de Existência
- **WHEN** o sistema valida uma referência no mapa
- **THEN** ele verifica de forma estrita se todos os `pontos_uids` existem nos pontos de interesse do SVG ou frontmatter daquele mapa, rejeitando correspondências parciais ou inválidas

### Requirement: Escopo Implícito e Explícito de Referências
O sistema SHALL priorizar a resolução de referências através do identificador imutável `alvo_uid`. Caso esse campo não esteja disponível (compatibilidade com croquis não migrados), o sistema SHALL recorrer à resolução legada por strings textuais (`escalada`, `setor`, `grupo`), assumindo que uma `Referencia` apontando para uma `escalada` (sem definir `setor` ou `grupo`) pertence ao Setor em que o `Mapa` está aninhado.

#### Scenario: Referência em Mapa de Setor
- **WHEN** a referência possui `alvo_uid` preenchido
- **THEN** o sistema resolve a referência diretamente para a entidade correspondente em tempo O(1), com imunidade total a renomeações de nomes ou movimentações de setor

#### Scenario: Referência em Mapa de Grupo (Cross-link/Falta de escopo)
- **WHEN** a referência não possui `alvo_uid` e depende exclusivamente de campos legados
- **THEN** o sistema resolve a referência procurando a escalada pelo nome dentro do escopo do setor correspondente, emitindo um warning se um mapa de grupo referenciar uma escalada sem prover o setor

## ADDED Requirements

### Requirement: Adoção do Campo Rotulo em Pontos de Interesse
O sistema SHALL adotar o termo `rotulo` (em português brasileiro) no Protobuf e nos arquivos fontes para representar o código visual da rota exibido na foto do croqui (ex: "11", "12A", "E1"), marcando o campo `label` como deprecado no Protobuf.

#### Scenario: Renderização e Edição de Rótulo
- **WHEN** o usuário visualiza ou edita um ponto de interesse no mapa
- **THEN** o sistema exibe e armazena o valor sob o atributo `rotulo`, mantendo o preenchimento de `label` no binário compilado para retrocompatibilidade com versões antigas do app

### Requirement: Preservação de Compatibilidade no Binário Compilado
O compilador SHALL serializar os campos `alvo_uid` e `pontos_uids` diretamente no `compilado.binarypb`, e preencher automaticamente em memória os campos deprecados `escalada`, `setor`, `grupo` e `label` para preservar o funcionamento de versões anteriores do app.

#### Scenario: Exportação para Binário Compilado
- **WHEN** o `deploy_generated` compila as referências de um mapa
- **THEN** ele grava `alvo_uid` e `pontos_uids` no Protobuf compilado e preenche em memória os nomes legados correspondentes no arquivo binário final
