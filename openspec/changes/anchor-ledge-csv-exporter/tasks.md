## 1. Setup do Script e Carga do Protobuf

- [ ] 1.1 Criar o arquivo base do script em `scripts/exportar_para_anchor_ledge.py`.
- [ ] 1.2 Importar a biblioteca `protobuf` e os stubs do Aresta (`aresta_api.proto.croqui_pb2`).
- [ ] 1.3 Adicionar a função para carregar e desserializar `generated/<id>/compilado.binarypb` na mensagem `Croqui`.

## 2. Processamento e Mapeamento dos Dados

- [ ] 2.1 Criar a função para ler os descritores do enum `GrauVia` (ex: `Croqui.DESCRIPTOR...`) e gerar o mapa reverso de int -> string formatada com prefixo FR (ex: `7c+`).
- [ ] 2.2 Iterar sobre `croqui.picos`, e seus respectivos `setores` (resolvendo os arquivos de setor caso necessário).
- [ ] 2.3 Implementar a extração dos campos (nome, conquistadores da lista para string).
- [ ] 2.4 Determinar `status` e `boltMaterial` verificando qual campo do `oneof tipo` (via_esportiva, via_movel, projeto) está preenchido na escalada.
- [ ] 2.5 Atribuir os placeholders de `areaId` (ID do croqui) e `sectorId` (nome do setor).

## 3. Exportação e Geração do CSV

- [ ] 3.1 Utilizar o módulo `csv` nativo do Python para instanciar o escritor.
- [ ] 3.2 Imprimir o cabeçalho exato exigido pelo Anchor Ledge.
- [ ] 3.3 Gravar todas as linhas num arquivo de saída `.csv`.

## 4. Validação

- [ ] 4.1 Rodar `/opsx-apply` e executar o script.
- [ ] 4.2 Validar o CSV resultante confirmando se a formatação das colunas, da conversão dos graus e escape de strings estão de acordo com o pdf de referência.
