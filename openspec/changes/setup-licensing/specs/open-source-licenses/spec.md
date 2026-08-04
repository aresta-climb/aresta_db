## ADDED Requirements

### Requirement: Documentação da Licença de Código (GPLv3)
O sistema (repositório `aresta_db`) MUST conter o texto integral da licença GPLv3 em um arquivo raiz chamado `LICENSE`.

#### Scenario: Presença do arquivo LICENSE
- **WHEN** um usuário clona ou explora o repositório `aresta_db`
- **THEN** ele encontra o arquivo `LICENSE` na raiz com o texto da GNU General Public License v3.

### Requirement: Diretrizes de Contribuição com DCO
O repositório MUST ter um arquivo `CONTRIBUTING.md` (ou similar) que detalhe o requisito de utilizar o Developer Certificate of Origin (DCO) para todas as contribuições externas.

#### Scenario: Assinatura de Commits (Sign-off)
- **WHEN** um contribuidor lê as diretrizes de contribuição
- **THEN** ele é instruído a usar a flag `-s` (`git commit -s`) para adicionar a linha `Signed-off-by` em seus commits, atestando conformidade com o projeto.

### Requirement: Licenciamento da API (Apache 2.0)
A documentação ou repositório da API (`aresta_api`) MUST deixar explícito que o componente de API é licenciado sob Apache 2.0, permitindo integração ampla.

#### Scenario: Informação da Licença da API
- **WHEN** um desenvolvedor consulta a documentação/código da Aresta API
- **THEN** ele é informado de que aquele componente está sob a licença Apache 2.0.
