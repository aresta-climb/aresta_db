## Why

O aplicativo de destino, Anchor Ledge, requer um arquivo CSV em um formato específico para importar informações de rotas. Precisamos exportar os dados estruturados de croquis do Aresta (como o da Gruta da Lapinha), lendo a versão compilada em protobuf (`compilado.binarypb`), para que o usuário consiga fazer a importação de maneira precisa e confiável.

## What Changes

- Criação de um novo script Python (`scripts/exportar_para_anchor_ledge.py`).
- O script fará a leitura direta do arquivo `generated/<id>/compilado.binarypb`, desserializando a mensagem Protobuf principal do croqui.
- Extração dos dados das vias (`escaladas`) incluindo nome, graduação, e tipo da via.
- Como o Protobuf armazena a graduação como um enum numérico unificado, o script usará esse valor numérico para extrair o identificador da escala brasileira (`BR_`), formatando-o para uso amigável (ex: `BR_6SUP` -> `6sup`).
- Mapeamento das colunas faltantes e obrigatórias para o CSV, como `areaId` (ID do croqui) e `sectorId` (nome do setor).
- Exportação dessas informações consolidadas num arquivo `.csv` único com codificação correta e campos separados por vírgula.

## Capabilities

### New Capabilities
- `exportacao-csv-anchor-ledge`: Capacidade de ler um croqui compilado do Aresta (em formato protobuf binário) e convertê-lo para o esquema CSV específico do aplicativo Anchor Ledge.

### Modified Capabilities

- Nenhuma capacidade existente modificada.

## Impact

- Impacto isolado: a criação do script não afeta o funcionamento de scripts ou dados existentes. Apenas lê dados atuais e exporta um arquivo CSV de saída.
