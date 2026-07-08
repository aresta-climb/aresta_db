## ADDED Requirements

### Requirement: Ler o protobuf compilado
O sistema SHALL ser capaz de abrir e desserializar o arquivo `generated/<id>/compilado.binarypb` usando o proto compilado correspondente à mensagem `Croqui`.

#### Scenario: Sucesso na leitura do protobuf
- **WHEN** o usuário executar o script passando um id de croqui válido que possua versão compilada
- **THEN** o script deve abrir `compilado.binarypb`, parsear os bytes para o objeto Python Protobuf, e acessar picos, setores e escaladas diretamente como atributos.

### Requirement: Mapeamento de campos Anchor Ledge via Protobuf
O sistema SHALL mapear as propriedades de uma rota lidas do objeto Protobuf para os campos exigidos pelo CSV do Anchor Ledge. Isso inclui mapear `nome` para `name`, `dificuldade` para `grade` com base no valor inteiro (enum), e gerar os campos `status` e `boltMaterial` de acordo com a mensagem instanciada no `oneof tipo` (ex: `via_movel`, `via_esportiva`, `projeto`).

#### Scenario: Conversão da graduação nativa
- **WHEN** uma via possuir graduação definida (o campo inteiro de `dificuldade`)
- **THEN** o script deverá inspecionar o enum do protobuf para achar a variante iniciada em `FR_` correspondente àquele inteiro, converte-la para minúsculo e trocar `_MAIS` por `+`.

#### Scenario: Determinação do Status e Material
- **WHEN** uma via for do tipo `projeto` no proto (enum GrauVia = PROJETO) ou similar (se for abordado assim)
- **THEN** o status exportado deve ser `CLOSED`.
- **WHEN** uma via for do tipo `via_movel`
- **THEN** o `boltMaterial` exportado deve ser `TRAD`.

### Requirement: Preenchimento de IDs
O sistema SHALL utilizar o próprio id do croqui como placeholder para `areaId`, e o nome do setor do proto para `sectorId`, deixando explícito no CSV os placeholders que o usuário terá de alterar manualmente antes do upload.

#### Scenario: Geração do arquivo CSV
- **WHEN** a extração e o mapeamento estiverem concluídos
- **THEN** o script deve salvar todos os dados em um único arquivo CSV compatível, assegurando que campos textuais que possam conter vírgulas ou aspas sejam adequadamente escapados.
