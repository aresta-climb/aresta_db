## RENAMED Requirements
- FROM: `### Requirement: Documentação da Licença de Código (GPLv3)`
- TO: `### Requirement: Documentação da Licença de Código (MPL 2.0)`

## MODIFIED Requirements

### Requirement: Documentação da Licença de Código (MPL 2.0)
O sistema (repositório `aresta_db`) MUST conter o texto integral da licença Mozilla Public License 2.0 (MPL 2.0) em um arquivo raiz chamado `LICENSE`. Além disso, todos os arquivos-fonte de código do repositório (`.py`, scripts de build e ferramentas de suporte) MUST conter o cabeçalho SPDX identificando a licença MPL 2.0 (`SPDX-License-Identifier: MPL-2.0`).

#### Scenario: Presença do arquivo LICENSE
- **WHEN** um usuário clona ou explora o repositório `aresta_db`
- **THEN** ele encontra o arquivo `LICENSE` na raiz contendo o texto integral da Mozilla Public License Version 2.0.

#### Scenario: Identificadores SPDX nos arquivos de código
- **WHEN** um arquivo de código-fonte Python ou script do `aresta_db` é inspecionado
- **THEN** ele inicia com o cabeçalho `# SPDX-License-Identifier: MPL-2.0`.
