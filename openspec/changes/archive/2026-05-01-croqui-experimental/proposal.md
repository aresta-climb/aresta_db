## Why

A criação do formato de Croqui Experimental permite que autores locais editem croquis de escalada no Editor Aresta de maneira contínua, garantindo controle de versão local e a facilidade de portabilidade entre máquinas (importação/exportação). Isso resolve a necessidade de editar croquis fora do repositório principal do GitHub da base de dados, permitindo a criação e edição independente e local de dados de forma padronizada.

## What Changes

- Criação do diretório de armazenamento no local storage: `croquis_experimentais/`.
- Definição do formato e da árvore de diretórios do croqui experimental (`<timestamp>_<pais>_<estado>_<cidade>_<nome_do_pico>/`).
- Estruturação do conteúdo interno em subpastas `database/` (dados descompilados), `compilado/` (dados compilados) e `.git` (repositório local de controle de versão).
- Suporte para exportação e importação de croquis experimentais compactando a pasta no formato ZIP e renomeando a extensão do arquivo para `.croqui`.
- Integração da estrutura de dados à definição `CroquiExperimental` no Protobuf `aresta_api/proto/croqui_experimental.proto`.

## Capabilities

### New Capabilities
- `croqui-experimental-format`: Definição do formato de armazenamento local do croqui experimental, estrutura de pastas, ciclo de vida (importação/exportação via arquivo `.croqui`) e controle de versão via Git local.

### Modified Capabilities
- Nenhuma

## Impact

- Sistema de gerenciamento de arquivos locais do Editor Aresta.
- Processos de compilação e descompilação de croquis deverão suportar a nova estrutura e referências relativas para as imagens.
- Interface de importação/exportação do aplicativo.
