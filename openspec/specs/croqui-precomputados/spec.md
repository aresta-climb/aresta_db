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

### Requirement: Pré-computação de Tamanho de Download do Croqui
A biblioteca de cálculo de tamanho e o pipeline de compilação do índice DEVEM (MUST) computar a soma total do tamanho em bytes de todos os arquivos requeridos para download offline de cada croqui (`compilado.binarypb` somado a todas as imagens válidas em `imagens/`, desconsiderando diretórios de artefatos intermediários como `raw_mapas`) e gravar esse valor no campo `resumo.precomputados.tamanho_download_bytes` do `indice.binarypb`.

#### Scenario: Cálculo isolado via biblioteca de tamanho
- **WHEN** a biblioteca `calcular_tamanho_croqui_lib` processa um croqui contendo `compilado.binarypb` e pasta `imagens/`
- **THEN** a função retorna o tamanho acumulado exato em bytes
- **AND** quaisquer arquivos contidos em subdiretórios excluídos (ex: `raw_mapas`) são ignorados na contagem.

#### Scenario: Compilação do índice com tamanho pré-computado
- **WHEN** o pipeline de deploy gera os croquis e monta o `indice.binarypb`
- **THEN** cada `ResumoCroqui` no índice possui `precomputados.tamanho_download_bytes` estritamente maior que zero
- **AND** o valor gravado corresponde fielmente ao tamanho em bytes retornado pela biblioteca para o croqui.

#### Scenario: Reflexão no arquivo de depuração indice.yaml
- **WHEN** o arquivo `indice.yaml` é exportado para inspeção e depuração
- **THEN** a chave `tamanho_download_bytes` está presente sob a seção `precomputados` de cada croqui com o respectivo valor numérico.
