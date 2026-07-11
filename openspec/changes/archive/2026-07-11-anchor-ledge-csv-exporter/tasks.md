## 0. Testes Unitários e TDD (Test-Driven Development)

- [x] 0.1 Criar o arquivo de testes em `scripts/exportar_para_anchor_ledge_test.py`.
- [x] 0.2 Escrever testes unitários para a função de conversão da graduação (garantindo que `BR_6SUP` retorne `6sup` e lidando com falhas ou valores desconhecidos).
- [x] 0.3 Escrever testes unitários para a extração e formatação de metadados estendidos (verificando `height`, `bolts`, anos, e `stars` de `destaque`).
- [x] 0.4 Escrever testes unitários para o processamento de um setor e extração das listas de escaladas.
- [x] 0.5 Assegurar que os testes cubram 100% das branches de código da funcionalidade que será implementada em seguida (e falhem, por estarmos na fase Red do TDD).

## 1. Setup do Script e Carga do Protobuf

- [x] 1.1 Criar o arquivo base do script em `scripts/exportar_para_anchor_ledge.py`, garantindo que todas as funções possuam Docstrings completas em português (seguindo PRINCIPIOS.md).
- [x] 1.2 Importar a biblioteca `protobuf` e os stubs do Aresta (`aresta_api.proto.croqui_pb2`).
- [x] 1.3 Implementar a função documentada para carregar e desserializar `generated/<id>/compilado.binarypb` na mensagem `Croqui`.
- [x] 1.4 Rodar os testes para validar se a fundação está passando (TDD Fase Green).

## 2. Iteração e Mapeamento de Dados (Camada de Aplicação)

- [x] 2.1 Implementar a função de leitura de descritores do enum `GrauVia` (ex: `Croqui.DESCRIPTOR...`) gerando o mapa reverso de int -> string formatada com prefixo BR (ex: `BR_6SUP` -> `6sup`).
- [x] 2.2 Iterar sobre `croqui.picos`, e seus respectivos `setores` (resolvendo os arquivos de setor caso necessário).
- [x] 2.3 Implementar a extração dos campos (nome, conquistadores da lista para string) e dos metadados estendidos (extrair `height` de `extensao`, `bolts` de `quantidade_protecoes_intermediarias`, extrair o ano para `faYear` dos 4 primeiros dígitos de `data_abertura`, extrair o ano para `rebolted` dos 4 últimos dígitos de `data_manutencao`, e `stars` derivado de `destaque`).
- [x] 2.4 Determinar `status` e `boltMaterial` verificando qual campo do `oneof tipo` (via_esportiva, via_movel, projeto) está preenchido na escalada.
- [x] 2.5 Atribuir os placeholders de `areaId` (ID do croqui) e `sectorId` (nome do setor).
- [x] 2.6 Refatorar e verificar se a cobertura de testes de tudo isso continua em 100%.

## 3. Geração do CSV (Camada de I/O)

- [x] 3.1 Utilizar o módulo `csv` nativo do Python para instanciar o escritor.
- [x] 3.2 Imprimir o cabeçalho exato exigido pelo Anchor Ledge.
- [x] 3.3 Gravar todas as linhas num arquivo de saída `.csv`.

## 4. Quality Assurance e Refatoração

- [x] 4.1 Confirmar que o código adere completamente a `PRINCIPIOS.md` (português, simplicidade, TDD, docstrings).
- [x] 4.2 Validar o CSV resultante no croqui da Gruta da Lapinha, confirmando se a formatação das colunas, da conversão dos graus e escape de strings estão de acordo com o pdf de referência.
