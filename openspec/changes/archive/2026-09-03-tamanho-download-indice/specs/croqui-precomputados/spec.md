## ADDED Requirements

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
