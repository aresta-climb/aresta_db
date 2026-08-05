## Architecture

A solução adotada envolverá uma varredura sobre todos os arquivos fonte de dados (`.yaml` e `.md`) no processo do pipeline de geração/deploy, ou, mais simplesmente, uma rotina utilitária que adiciona os comentários ao topo se estiverem ausentes.

### Componentes Afetados
- `scripts/preparar_submissao_lib.py`: A principal biblioteca de parse, correção e compilação do banco de dados de croquis.
- Funções afetadas indiretamente: `processar_croqui_yaml`, `salvar_md_com_frontmatter`, e `corrigir_database`.

### Abordagem Técnica
Como as bibliotecas Python (ex: `PyYAML`) frequentemente ignoram ou corrompem comentários no momento de leitura/escrita, injetar o comentário em formato de chave de dicionário quebra o contrato Protobuf. A solução é atuar sobre o nível do arquivo texto.

Foi escolhida a seguinte heurística:
1. Uma função dedicada `garantir_comentarios_licenca(file_path: Path)` lê o arquivo texto bruto.
2. Verifica se a linha `SPDX-License-Identifier` existe.
3. Se não existir, insere as seguintes duas linhas:
   ```yaml
   # SPDX-License-Identifier: ODbL-1.0
   # Copyright (C) 2026 Aresta Contributors
   ```
4. Em arquivos `.yaml`, insere no começo do arquivo.
5. Em arquivos `.md`, se a primeira linha for `---` (frontmatter), insere na segunda linha, garantindo que o cabeçalho permaneça dentro do bloco YAML e não quebre a leitura.
6. A função `corrigir_database` invoca a injeção em todos os arquivos fonte `.yaml` e `.md` ao final de sua execução. Dessa forma, ela atua tanto em arquivos já modificados (que perderam os comentários pelo dump) quanto nos intactos, garantindo os comentários sempre.

## Constraints & Trade-offs
- O uso de parsing e escrita manual em texto para garantir as linhas no topo pode parecer verboso, mas evita reescrever todo o fluxo de parsing YAML para uma ferramenta baseada em AST preservadora de comentários (como o pacote `ruamel.yaml`), que traria mais peso e bugs de formatação ao projeto atual.
