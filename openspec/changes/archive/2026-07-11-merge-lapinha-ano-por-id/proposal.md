## Why

Temos um arquivo CSV completo e revisado contendo informações ricas sobre as vias da Gruta da Lapinha, incluindo o ano de conquista (103 vias com datas que hoje não temos no croqui). Precisamos de uma forma automatizada de realizar esse merge de dados para garantir que a `data_abertura` (e possivelmente outras métricas) estejam consistentes no croqui YAML (`br_mg_lagoa_santa_gruta_da_lapinha`), sem perder os ajustes de nome já feitos no próprio croqui.

## What Changes

- Criação de um script (Python ou equivalente em node) para extrair os dados do CSV `Vias da Lapinha.xlsx - Plan1.csv` e mesclar com os arquivos `setor_mapa_*.md`.
- Uso do ID numérico (coluna `N°` do CSV batendo com o `ids` numérico do YAML) como chave primária do merge, garantindo que não tenhamos falhas de `fuzzy match`.
- Estratégia de resolução de nomes: Para nomes divergentes (como "Bem Moon" vs "Ben Moon"), a versão do YAML (Croqui) será priorizada, pois já passou por revisão prévia e costuma estar mais correta, ou o script fará um registro/log dessas alterações.
- A alteração aplicará as datas de abertura no formato esperado (`data_abertura`) para mais de 100 vias.

## Capabilities

### New Capabilities
- `merge-dados-lapinha`: Scripts temporários/utilitários para mesclar dados externos (CSV) no banco de dados do croqui com resolução de conflito de nomenclatura.

### Modified Capabilities
- Vazio (Não há alteração nos requisitos de especificação de software existente).

## Impact

- Arquivos do banco de dados afetados: `C:\Renato\Devel\aresta-climb\aresta_db\database\br_mg_lagoa_santa_gruta_da_lapinha\setor_mapa_*.md`
- Todos os arquivos terão seus cabeçalhos YAML modificados (em especial o campo `data_abertura`).
