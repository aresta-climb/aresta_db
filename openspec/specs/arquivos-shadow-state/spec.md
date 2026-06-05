# arquivos-shadow-state Specification

## Purpose
Specifies the shadow state extensions mechanism to persist original file paths and track new file paths while editing `oneof` textual content in Protobuf, ensuring correct serialization to disk without losing file context or corrupting the final database.

## Requirements

### Requirement: Editor retém Caminho Original ao Editar Conteúdo
O sistema MUST armazenar o caminho original do arquivo em uma "extension" (ou campo invisível do editor) no Protobuf assim que o conteúdo for carregado ou editado, para sobreviver à restrição do "oneof" que limpa o caminho ao receber texto.

#### Scenario: Edição de conteúdo de um arquivo existente
- **WHEN** um arquivo possuir "caminho" populado no YAML e o usuário digitar algo no editor do Widget
- **THEN** o editor armazena esse caminho antigo em "caminho_original", apaga o "caminho" (via comportamento padrão do protobuf) e salva o texto em "conteudo".

### Requirement: Editor permite Renomeação mantendo Histórico
O sistema MUST suportar o uso de "caminho_novo" para referenciar o caminho de salvamento pretendido enquanto mantém o "caminho_original" salvo para fins de deleção. A UI de edição (view) MUST priorizar a leitura do "caminho_novo" da extensão para exibir o filename atual, já que o campo "caminho" nativo é limpo pelo Protobuf.

#### Scenario: Leitura do nome de arquivo pela UI
- **WHEN** a UI renderiza o componente ONEOF_CONTEUDO e o Protobuf possui texto no "conteudo"
- **THEN** a UI obtém o valor da extensão "caminho_novo" para preencher o input de filename, pois o campo nativo "caminho" estará vazio.

#### Scenario: Renomeação do nome de arquivo pelo usuário
- **WHEN** o usuário modificar o filename field da interface gráfica 
- **THEN** a UI salva o "caminho_novo" com o novo nome enquanto mantém intacto o "caminho_original" com o nome antigo.

### Requirement: Salvamento limpa Shadow State antes do YAML
O modelo de persistência no `CroquiModel` MUST ler os metadados virtuais para manipular o sistema de arquivos, limpar o disco dos "caminho_original" se tiverem sido renomeados, e MUST apagar completamente o Shadow State do Protobuf em memória antes da sua respectiva serialização para o YAML final.

#### Scenario: Operação final de disco
- **WHEN** a persistência rodar no `CroquiModel` e encontrar o campo "conteudo" com "caminho_novo"
- **THEN** escreve o conteúdo em disco no novo path, limpa os arquivos apontados pelo "caminho_original", apaga ambos os metadados do protobuf, esvazia o "conteudo" e atribui o caminho final ao "caminho", restaurando a validez completa do "oneof".

#### Scenario: Conteúdo puramente inline sem exportação
- **WHEN** o YAML possuir uma estrutura inline (sem "caminho") com conteúdo textual longo sem "caminho_novo"
- **THEN** a persistência não tenta ejetar o conteúdo pro disco e o preserva puramente embutido no YAML.

### Requirement: Compilador Rejeita Extensões Vazadas
O sistema de build (`deploy_generated.py`) MUST validar a integridade dos dados lidos do disco e falhar a compilação se encontrar alguma mensagem em disco contendo extensões do Shadow State, evitando assim corrupção e vazamento de metadados temporários para os dados de produção.

#### Scenario: Compilação de um banco de dados sujo
- **WHEN** o `deploy_generated.py` ler os YAMLs e o Protobuf resultante possuir propriedades de extensões (`caminho_original` ou `caminho_novo`) preenchidas
- **THEN** o compilador levanta um erro claro impedindo a geração do banco de dados, reportando a inconsistência.
