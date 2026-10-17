# editor-serializacao-croqui Specification

## Purpose
Especificação das regras de serialização determinística de arquivos YAML e Markdown de croquis, padronização de quebras de linha em LF e escrita condicional no disco entre o editor e o pipeline de compilação.

## Requirements

### Requirement: Unificação do Representer YAML entre Editor e Compilador
O sistema SHALL utilizar uma única função canônica de representação de strings no PyYAML (`representar_string_yaml`) registrada tanto no `yaml.Dumper` quanto no `yaml.SafeDumper`, garantindo formatação idêntica entre o salvamento do editor (`CroquiModel`, `TarefaSalvamento`, `GerenciadorCroquiExperimental`) e o pipeline de compilação (`preparar_submissao_lib`, `markdown_frontmatter_lib`, `deploy_generated`).

#### Scenario: Serialização de strings multilinhas em bloco literal
- **WHEN** um campo textual (como `descricao` ou `conteudo`) contiver quebras de linha (`\n`) durante a serialização no editor ou no compilador
- **THEN** o serializador YAML SHALL representá-lo utilizando o estilo de bloco literal (`|` / `|-`), sem convertê-lo para string entre aspas simples (`'...'`)

#### Scenario: Serialização de strings numéricas com aspas simples
- **WHEN** uma string for composta exclusivamente por dígitos (positivos como `'08'`, `'1994'` ou negativos como `'-1'`)
- **THEN** o serializador YAML SHALL representá-la entre aspas simples (`'`), preservando o tipo string em parsers YAML

#### Scenario: Não interferência no estado global do PyYAML após salvamento no editor
- **WHEN** `CroquiModel.extrair_arquivos_e_serializar` for executado antes de `deploy()` no mesmo processo Python
- **THEN** o representer ativo no `yaml.Dumper` SHALL continuar formatando strings multilinhas com `|` em `compilado.yaml` e `indice.yaml`

### Requirement: Escrita Textual Condicional e Padronizada em LF
O sistema SHALL gravar arquivos textuais estruturados (`.yaml` e `.md`) sempre com quebras de linha `LF` (`\n`) e SHALL abster-se de sobrescrever o arquivo no disco quando o novo conteúdo normalizado em `LF` for idêntico ao conteúdo já existente no disco (também normalizado em `LF`).

#### Scenario: Salvamento de croqui com setores não modificados
- **WHEN** o usuário editar apenas um setor de um croqui e acionar o salvamento no editor
- **THEN** os arquivos `.md` dos demais setores, grupos, mapas gerais e botões cujo conteúdo lógico não mudou SHALL permanecer intocados no disco (preservando seu `mtime` original)

#### Scenario: Padronização estrita de LF em todos os pontos de escrita
- **WHEN** `croqui.yaml`, arquivos `.md` com frontmatter, `compilado.yaml`, `indice.yaml` ou `STATUS_CROQUIS.md` forem gravados em qualquer sistema operacional (incluindo Windows)
- **THEN** os bytes gravados no disco SHALL conter exclusivamente `\n` (`LF`) como separador de linhas, sem ocorrências de `\r\n` (`CRLF`)

### Requirement: Atualização Condicional do Relatório de Saúde dos Croquis
O script `scripts/medir_saude_croquis.py` SHALL comparar a tabela Markdown gerada com a tabela presente no arquivo `STATUS_CROQUIS.md` existente e SHALL regravar o arquivo (atualizando o cabeçalho `Relatório gerado em:`) somente quando houver alteração real no conteúdo da tabela.

#### Scenario: Execução de medição de saúde sem mudanças nos indicadores
- **WHEN** `medir_saude_croquis.py` for executado e a tabela de status resultante for idêntica à tabela já presente em `STATUS_CROQUIS.md`
- **THEN** o arquivo `STATUS_CROQUIS.md` SHALL permanecer inalterado no disco, mantendo a data/hora anterior de geração
