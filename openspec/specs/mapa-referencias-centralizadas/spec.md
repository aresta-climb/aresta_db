# mapa-referencias-centralizadas Specification

## Purpose
Centraliza todas as referências de escaladas e pontos de interesse diretamente no objeto Mapa, vinculando traçados vetoriais e fotos a UIDs imutáveis.

## Requirements

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

### Requirement: Geometria Ilimitada de Rota
O sistema SHALL usar uma lista ordenada de `ids` (repeated string) na Referência para definir o caminho de uma escalada no mapa, removendo a restrição de apenas início, meio e fim.

#### Scenario: Renderização de Rota Longa
- **WHEN** a referência possui 5 IDs de POIs
- **THEN** o sistema as trata como um caminho ordenado interligando os 5 pontos em sequência

### Requirement: Ajuste Fino de Câmera
O sistema SHALL permitir que cada referência sobrescreva o comportamento padrão de foco da câmera quando essa escalada for selecionada via interface.

#### Scenario: Foco Específico
- **WHEN** a referência define `AjusteDeCamera` com `posicao_vertical = 60`
- **THEN** a interface de renderização deve centralizar a referência de modo que ela fique a 60% da tela (acima do meio)

### Requirement: Parsing de IDs Compostos e Distribuídos
O sistema SHALL suportar a distribuição estrita de IDs combinados separados por barras e quebra lógica de letras e números para garantir o referenciamento preciso entre POIs e metadados.

#### Scenario: Distribuição Estrita com Barras
- **WHEN** o ID fornecido no POI é `11A/B`
- **THEN** o sistema mapeia os IDs como `11A` e `11B`

#### Scenario: Quebra de Letras e Números
- **WHEN** o ID possui componentes concatenados como letras, símbolos e números (ex: `2A▲`)
- **THEN** o sistema pode desconstruir o ID para realizar matching mais flexível ou distribuí-lo (quando houver suporte futuro no modelo)

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
