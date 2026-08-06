## ADDED Requirements

### Requirement: Pré-computados de Setor
O processo de build do croqui SHALL injetar um sub-proto `precomputados` contendo a soma das escaladas de cada setor.

#### Scenario: Compilação de setor
- **WHEN** o setor é compilado e possui 5 vias na propriedade escaladas
- **THEN** o `Setor.precomputados.total_escaladas` deve ser igual a 5

### Requirement: Pré-computados de Grupo
O processo de build do croqui SHALL injetar um sub-proto `precomputados` em um grupo, contendo a soma das escaladas de todos os setores agregados a ele.

#### Scenario: Compilação de grupo
- **WHEN** o grupo é compilado e possui o setor A com 3 vias e o setor B com 2 vias
- **THEN** o `Grupo.precomputados.total_escaladas` deve ser igual a 5

### Requirement: Pré-computados de Pico e Índice
O processo de build do croqui SHALL injetar totais agregados de escaladas, setores e grupos no Pico e repassá-los ao `ResumoCroqui` no `indice.binarypb`.

#### Scenario: Compilação global
- **WHEN** o croqui é compilado
- **THEN** o `Pico.precomputados` e o `ResumoCroqui.precomputados` devem conter `total_escaladas`, `total_setores` e `total_grupos` corretos e devidamente somados.
