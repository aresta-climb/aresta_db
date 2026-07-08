## Context

Os administradores e contribuidores do Aresta precisam enviar os dados de croquis gerados localmente para o aplicativo Anchor Ledge através de arquivos CSV. Em vez de ler os arquivos YAML em formato não estruturado, o Aresta já possui uma pipeline que compila o croqui inteiro em um arquivo `.binarypb` rigoroso com todos os dados tratados e enums convertidos.

## Goals / Non-Goals

**Goals:**
- Prover um script (CLI) em Python fácil de rodar no terminal, para exportar rapidamente os dados de um croqui compilado.
- Utilizar a desserialização do `compilado.binarypb` usando protobuf para iterar pelos dados sem risco de parse incorreto.
- Fazer a conversão direta da graduação baseada no enum interno do Protobuf (`GrauVia`), extraindo o nome do enum francês equivalente ao inteiro armazenado e formatando-o (ex: `FR_7C_MAIS` -> `7c+`).
- Mapear corretamente as informações para os campos obrigatórios e não-obrigatórios exigidos pelo sistema Anchor Ledge.

**Non-Goals:**
- Fazer integração por API ou de forma automática com o Anchor Ledge; a importação é manual pelo usuário.
- Mapeamento dinâmico automático de IDs verdadeiros do banco de dados do Anchor Ledge. O script usará o ID de croqui e o nome do setor como placeholders, exigindo ajuste posterior no CSV (por solicitação explícita do usuário).

## Decisions

- **Leitura do Protobuf**: O script importará o módulo protobuf compilado (`aresta_api.proto.croqui_pb2`) e chamará `ParseFromString` no arquivo `generated/<id>/compilado.binarypb`. Isso elimina a necessidade de parsers YAML ou de lidar com a estrutura fragmentada de arquivos Markdown.
- **Placeholders de Identificação**: Os campos `areaId` vão conter o nome base da pasta (ex: `br_mg_lagoa_santa_gruta_da_lapinha`) e `sectorId` conterá o próprio nome do setor (`setor.nome`).
- **Grade Mapping**: Aproveitaremos a tabela de descritores do enum `GrauVia` no Python (`Croqui.DESCRIPTOR...`) para pegar o valor inteiro salvo e encontrar o nome da chave que comece com `FR_`, aplicando replace simples (ex: `_MAIS` para `+`).
- **Tratamento de Strings no CSV**: Utilização do módulo interno do Python `csv`.

## Risks / Trade-offs

- **Dependência do Protobuf Compilado**: O script exigirá que o croqui já tenha sido compilado (comando de build do Aresta) para que o `compilado.binarypb` exista e esteja atualizado. Isso é um trade-off positivo pois garante a qualidade dos dados.
- **Revisão Manual dos IDs**: Como geramos placeholders, se o usuário não substituí-los antes de enviar pro Anchor Ledge, a importação vai falhar lá (pois esperam inteiros). Como foi explicitamente pedido, consideramos isso um trade-off aceitável.
