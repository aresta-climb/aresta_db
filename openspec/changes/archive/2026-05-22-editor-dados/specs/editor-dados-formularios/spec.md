## ADDED Requirements

### Requirement: Geração Dinâmica de Formulários
O sistema SHALL criar e exibir formulários na área de edição principal baseados na definição do campo do protobuf selecionado.

#### Scenario: Edição de Campos Escalares
- **WHEN** um nó do tipo escalar (string, inteiro, boolean) é selecionado
- **THEN** o sistema SHALL exibir o widget correto (`QLineEdit`, `QSpinBox`, `QCheckBox`) contendo o valor atual ou estado default indicando campo vazio.

#### Scenario: Edição de Campos Repetidos
- **WHEN** um nó do tipo `repeated` é selecionado
- **THEN** o sistema SHALL exibir uma lista de itens com botões de adicionar (+) e remover (-).

### Requirement: Documentação e Textos da Interface Guiados pelo Protobuf
O sistema SHALL extrair dinamicamente a documentação de cada campo (explicações e descrições exibidas na UI) dos comentários presentes nos arquivos `.proto`. Da mesma forma, os rótulos (labels) dos campos SHALL ser extraídos dos nomes dos campos no protobuf ou de field/message options explicitamente definidos, de forma a não haver strings de documentação "hardcoded" na aplicação do editor.

#### Scenario: Visualização da Documentação de um Campo
- **WHEN** o formulário de um campo é exibido
- **THEN** o sistema SHALL mostrar o comentário presente no arquivo `.proto` (referente àquele campo) como documentação associada a ele na tela.

#### Scenario: Uso de Opções para Nomenclatura
- **WHEN** um campo do protobuf contém uma opção customizada (ex: referente a UI label)
- **THEN** o sistema SHALL priorizar essa string para o título/label do campo em vez do próprio identificador base do campo.

