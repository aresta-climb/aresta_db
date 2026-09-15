## MODIFIED Requirements

### Requirement: Preservação e injeção de comentários de licença nos arquivos da base de dados
O sistema MUST, durante a compilação (especificamente ao final de `corrigir_database`), varrer todos os arquivos Markdown (`.md`) e YAML (`.yaml`) fonte e assegurar a existência das duas linhas de comentários referentes à licença ODbL e ao Copyright:
```yaml
# SPDX-License-Identifier: ODbL-1.0
# Copyright (C) 2026 Aresta Climb Contributors
```
Isso deve ser feito de forma bruta (no nível de texto/string) para contornar o comportamento do parser `PyYAML`, que remove silenciosamente comentários originais durante os ciclos de leitura e escrita.

#### Scenario: Arquivo YAML ou MD que perdeu/não possui os comentários
- **WHEN** o arquivo (`croqui.yaml` ou `.md` com frontmatter) não possui a string `SPDX-License-Identifier` em nenhuma de suas linhas.
- **THEN** o script insere as duas linhas de comentário no topo do arquivo.
  - Para arquivos YAML: insere na linha 1.
  - Para arquivos MD com frontmatter (`---` na linha 1): insere logo abaixo, na linha 2.
- **AND** o arquivo é salvo no disco.

#### Scenario: Arquivo YAML ou MD já possui os comentários
- **WHEN** o arquivo já possui a string `SPDX-License-Identifier` em alguma de suas linhas.
- **THEN** o script considera que as licenças estão corretas e o arquivo não é modificado em disco.

#### Scenario: Arquivo MD sem frontmatter
- **WHEN** o arquivo `.md` não inicia com o marcador de frontmatter (`---`).
- **THEN** o script o ignora e nenhuma injeção é realizada.

#### Scenario: Falha transitória de I/O ao reescrever arquivo
- **WHEN** a tentativa de abrir o arquivo para reescrita com SPDX lançar um `OSError` transitório (como `[Errno 22] Invalid argument` ou `PermissionError [Errno 13]`).
- **THEN** o sistema SHALL efetuar até 3 retentativas com espera linear/exponencial antes de registrar falha no log.

## ADDED Requirements

### Requirement: Emissão nativa de comentários de licença na serialização do editor
Toda rotina do editor que salvar ou serializar arquivos `.md` com frontmatter ou arquivos `croqui.yaml` SHALL emitir os comentários de licença SPDX e Copyright diretamente no momento da escrita inicial.

#### Scenario: Salvamento de setor, grupo ou mapas pelo editor
- **WHEN** o editor salvar um objeto Markdown com frontmatter em disco.
- **THEN** o frontmatter gerado DEVE conter imediatamente as linhas `# SPDX-License-Identifier: ODbL-1.0` e `# Copyright (C) 2026 Aresta Climb Contributors` logo após a linha de abertura `---`.

#### Scenario: Salvamento de croqui.yaml pelo editor
- **WHEN** o editor salvar o arquivo `croqui.yaml` em disco.
- **THEN** o arquivo YAML gerado DEVE conter no topo as linhas `# SPDX-License-Identifier: ODbL-1.0` e `# Copyright (C) 2026 Aresta Climb Contributors`.
