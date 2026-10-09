# editor-serializacao-croqui Specification

## Purpose

Define o contrato de persistência atômica e serialização limpa de croquis no disco pelo Editor Desktop, garantindo total isolamento de metadados temporários de edição e impedindo o vazamento de extensões de shadow state para o banco de dados fonte.

## Requirements

### Requirement: Isolamento Estrito de Shadow State na Serialização
O sistema SHALL garantir que todas as extensões e metadados de shadow state de edição em memória (`ext_metadados_arquivo`) sejam expurgados incondicionalmente antes de gravar o arquivo `croqui.yaml` ou qualquer arquivo Markdown (`.md`) no disco, mesmo quando os elementos contiverem apenas caminho relativo ou não possuírem conteúdo inline expandido.

#### Scenario: Serialização de croqui com mapas gerais contendo metadados de arquivo
- **WHEN** um croqui possuir `mapas_gerais` referenciado por caminho e com extensão de metadados de arquivo associada
- **THEN** a serialização para o disco SHALL gravar o arquivo `croqui.yaml` contendo apenas os campos canônicos, sem qualquer chave de extensão `ext_metadados_arquivo`

#### Scenario: Serialização de croqui com setores ou grupos contendo apenas caminho
- **WHEN** um setor ou grupo possuir a extensão `ext_metadados_arquivo` configurada mas estiver associado a um caminho de arquivo sem conteúdo inline carregado
- **THEN** a serialização para o disco SHALL desassociar a extensão e gravar `croqui.yaml` sem chaves de extensão de shadow state

#### Scenario: Validação pós-deploy sem extensões vazadas
- **WHEN** qualquer croqui serializado pelo editor for submetido à rotina de compilação e deploy
- **THEN** a validação `validar_sem_extensoes_vazadas` SHALL aprovar o diretório do croqui sem encontrar nenhuma ocorrência de `ext_metadados` em arquivos `.yaml` ou `.md`

### Requirement: Sanitização Recursiva de Dicionários Exportados
O sistema SHALL sanitizar recursivamente toda a estrutura de dicionários resultante de conversões Protobuf antes de gravar arquivos estruturados no disco (`croqui.yaml` e frontmatters de arquivos Markdown), removendo sumariamente qualquer chave que contenha `ext_metadados` ou corresponda a qualificadores de extensão com colchetes.

#### Scenario: Remoção de chaves de extensão no dicionário do croqui
- **WHEN** a mensagem `Croqui` for convertida em dicionário Python para gravação do `croqui.yaml`
- **THEN** o dicionário final resultante SHALL ser desprovido de quaisquer chaves iniciadas por `[` ou contendo `ext_metadados` em todos os níveis de profundidade

#### Scenario: Preservação de dados válidos durante a sanitização
- **WHEN** a sanitização recursiva for executada sobre a estrutura do croqui
- **THEN** todos os campos e atributos canônicos (como `id`, `uid`, `nome`, `picos`, `setores_ou_grupos`, `botoes` e caminhos) SHALL ser integralmente preservados sem mutações indevidas
