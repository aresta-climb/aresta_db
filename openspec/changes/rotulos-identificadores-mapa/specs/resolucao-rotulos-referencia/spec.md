## Purpose

Define as regras de extração e resolução de rótulos identificadores (codenomes) em referências visuais de mapas no aplicativo móvel e a validação de referências sem identificadores no processo de deploy e compilação de croquis.

## ADDED Requirements

### Requirement: Extração Sequencial de Rótulos em Traçados Vetoriais
O sistema no aplicativo móvel SHALL extrair os identificadores textuais de uma referência inspecionando cada ponto de interesse em `ref.ids` na ordem exata informada, coletando os rótulos de nós do tipo `CIRCULO_IDENTIFICADOR`, `INICIO_AGACHADO` e `FIM_TOP` que possuam `rotulo` preenchido.

#### Scenario: Referência com múltiplos segmentos vetoriais contendo início e fim
- **WHEN** uma referência contém uma lista de linhas onde o primeiro segmento possui um nó `CIRCULO_IDENTIFICADOR` com rótulo "5", os segmentos intermediários contêm apenas curvas ou passagens, e o último segmento possui um nó `FIM_TOP` com rótulo "C"
- **THEN** o sistema SHALL extrair os rótulos e formatar o codenome como "5-C"

#### Scenario: Referência com múltiplos círculos identificadores intermediários
- **WHEN** uma linha ou caminho de linhas contém uma sequência de nós identificadores como "SS", "2" e "TOP"
- **THEN** o sistema SHALL preservar a ordem de encontro dos nós e retornar "SS-2-TOP"

### Requirement: Ausência de Fallback para IDs Técnicos de Banco
O sistema no aplicativo móvel SHALL retornar uma string vazia caso nenhum ponto de interesse ou nó da referência possua rótulo/círculo identificador, e NÃO DEVE adicionar o ID técnico do ponto de interesse (`linha_XX` ou similar) aos rótulos exibidos.

#### Scenario: Linha sem nós de círculo identificador
- **WHEN** uma referência aponta exclusivamente para linhas ou pontos que não possuem círculos identificadores nem campo `label` preenchido
- **THEN** o resolvedor de rótulos SHALL retornar uma string vazia
- **AND** o aplicativo móvel SHALL omitir visualmente a pílula/badge de codenome no card da via e na lista do setor

### Requirement: Retrocompatibilidade com Pontos de Interesse Convencionais
O sistema SHALL extrair o valor do campo `label` de pontos de interesse que não sejam linhas vetoriais (círculos, retângulos ou quadrados avulsos) quando esse campo estiver preenchido e não vazio.

#### Scenario: Ponto tradicional com label preenchido
- **WHEN** uma referência aponta para um ponto de interesse circular tradicional que possui `label: "12"`
- **THEN** o sistema SHALL extrair "12" como rótulo identificador da referência

### Requirement: Deduplicação de Rótulos Adjacentes Idênticos
O sistema SHALL consolidar rótulos adjacentes consecutivos que possuam o mesmo valor textual exato.

#### Scenario: Segmentos adjacentes conectados compartilhando o mesmo rótulo
- **WHEN** dois segmentos de trajeto conectados se encontram em um nó compartilhado e ambos registram o identificador "5"
- **THEN** o sistema SHALL deduplicar a sequência retornando apenas uma ocorrência "5"

### Requirement: Alerta de Compilação para Referências sem Identificador
O processo de validação e compilação do croqui (`deploy_generated.py` e `validar_referencias_mapa`) SHALL emitir uma mensagem de aviso no log caso uma referência no mapa não possua nenhum rótulo ou círculo identificador preenchido.

#### Scenario: Detecção de referência órfã de rótulo no deploy
- **WHEN** o compilador processa um mapa onde uma referência aponta para pontos que não possuem `label` nem nós com `rotulo` em círculo identificador
- **THEN** o compilador SHALL emitir um aviso contendo exatamente a frase "não possui label ou rótulo em círculo identificador e não exibirá identificador no mapa do aplicativo"
- **AND** a compilação do croqui NÃO SHALL ser abortada por esse aviso
