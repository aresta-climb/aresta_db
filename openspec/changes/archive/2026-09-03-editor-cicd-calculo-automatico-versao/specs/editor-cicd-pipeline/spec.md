## ADDED Requirements

### Requirement: Seleção Parametrizada do Tipo de Release no Workflow
O workflow de lançamento DEVE (SHALL) permitir ao operador selecionar o tipo de incremento de versão (`patch`, `minor`, `major` ou `custom`), calculando deterministicamente o número de versão semântico oficial a ser lançado antes das etapas de compilação e empacotamento.

#### Scenario: Operador seleciona incremento patch padrão
- **WHEN** o workflow for acionado com `bump_type: patch` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `0.2.1`

#### Scenario: Operador seleciona incremento minor
- **WHEN** o workflow for acionado com `bump_type: minor` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `0.3.0`

#### Scenario: Operador seleciona incremento major
- **WHEN** o workflow for acionado com `bump_type: major` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `1.0.0`

#### Scenario: Operador fornece versão customizada válida
- **WHEN** o workflow for acionado com `bump_type: custom` e informar `custom_version: 0.5.0`
- **THEN** o sistema valida a conformidade SemVer e utiliza a versão `0.5.0` para o lançamento
