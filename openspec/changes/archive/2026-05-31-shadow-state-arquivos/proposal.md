## Why

Atualmente, os campos de arquivo como `ArquivoMarkdown`, `ArquivoSetor` e `ArquivoGrupo` utilizam um `oneof` no Protobuf que abriga mutuamente o `caminho` e o `conteudo`. Quando o usuário edita o texto no editor e preenche o campo `conteudo`, o `caminho` original é apagado pela restrição do `oneof`. Isso força a interface gráfica (`widget_editor_dados.py`) a gerenciar "shadow states" manuais gigantescos e frágeis (`arquivos_carregados`, `caminhos_originais`) para se lembrar de qual arquivo estava sendo modificado. Resolver isso simplificará massivamente o editor, além de trazer resiliência às operações de deleção/renomeação.

## What Changes

- Implementaremos o padrão de "Shadow State" nas mensagens Protobuf através de extensões (ou metadados invisíveis de interface). Isso permitirá reter o `caminho_original` (histórico) e o `caminho_novo` (destino) em runtime.
- O rigidez do `oneof` (`caminho` vs `conteudo`) será mantida, garantindo que o `croqui.proto` continue protegendo os consumidores externos da API.
- A Interface de Edição será simplificada para tratar o próprio Protobuf como a única "Fonte da Verdade", eliminando os dicionários paralelos do componente.
- O ciclo de salvamento (no `CroquiModel`) interceptará as extensões e manipulará o sistema de arquivos baseando-se no `caminho_original` e `caminho_novo`, limpando o disco caso necessário (arquivos desatualizados ou renomeados) e limpando as extensões antes de serializar o YAML.

## Capabilities

### New Capabilities
- `arquivos-shadow-state`: Gerenciamento temporário de ciclo de vida de arquivos atrelados ao Protobuf via "Shadow State" durante o runtime do Editor, suportando deleções, renomeações e modificações limpas de Arquivos no disco.

### Modified Capabilities

## Impact

- **Protobuf**: O `croqui.proto` receberá a estrutura necessária para estender os dados com os caminhos virtuais.
- **Views**: Redução de complexidade em `widget_editor_dados.py` e `area_principal.py`, que dependiam ativamente da injeção dos dicionários de estado.
- **Model / Scripts**: Refatoração do `CroquiModel` e de `preparar_submissao_lib.py` para processar a persistência usando o histórico da Extensão antes de removê-la para o YAML final.
