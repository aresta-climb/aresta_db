# Padronização e Qualidade de Código com Ruff Specification

## Purpose

Define os padrões, regras e mecanismos automatizados de validação de qualidade estática de código (linting e formatação) para a base Python do aresta_db utilizando o ecossistema Ruff.

## Requirements

### Requirement: Verificação Automatizada de Lint e Formatação
O sistema SHALL verificar a conformidade sintática, ausência de imports ou variáveis mortas, ordenação de imports e boas práticas de tipagem e performance configuradas no `pyproject.toml` para o código Python do repositório.

#### Scenario: Código em conformidade com o padrão
- **WHEN** o comando `ruff check` e `ruff format --check` for executado sobre a base de código
- **THEN** o processo deve retornar código de saída 0 sem reportar erros ou alterações pendentes.

#### Scenario: Detecção de violações de estilo ou erros lógicos
- **WHEN** um arquivo contiver imports não utilizados, código inatingível ou formatação em desacordo com as regras
- **THEN** o comando deve retornar código de saída diferente de zero, indicando o arquivo, a linha, a coluna e o código da regra violada.

### Requirement: Isolamento de Artefatos Gerados e Temporários
O sistema SHALL ignorar completamente arquivos gerados por compiladores de Protocol Buffers (`*_pb2.py`, `*_pb2.pyi`) e diretórios temporários ou de build (`.venv`, `dist`, `build`, `scratch`).

#### Scenario: Arquivos gerados por compiladores presentes no repositório
- **WHEN** a ferramenta de lint ou formatação processar a árvore de arquivos
- **THEN** arquivos terminados em `_pb2.py` ou localizados sob `aresta_api/proto/generated` não devem ser analisados nem modificados.

### Requirement: Bloqueio Pré-Teste no Build do Editor
O utilitário de execução de testes do editor SHALL executar a validação de lint e formatação do Ruff antes de inicializar a suíte do Pytest, interrompendo o fluxo imediatamente caso violações sejam encontradas e orientando o desenvolvedor sobre como corrigi-las.

#### Scenario: Código do editor com violação de lint
- **WHEN** a função de testes do script de build do editor for acionada em um repositório com erro de lint
- **THEN** o processo deve exibir o diagnóstico no terminal, sugerir o comando `uv run ruff check --fix` e encerrar a execução com código de erro sem disparar o Pytest.

#### Scenario: Código do editor em conformidade
- **WHEN** o código do editor estiver em total conformidade com o Ruff
- **THEN** a validação deve passar silenciosamente ou com mensagens de confirmação e prosseguir diretamente para a execução dos testes do Pytest.

### Requirement: Fail-Fast no Pipeline de Pull Requests (CI)
O pipeline de validação de Pull Requests (`pr-code-validator.yml`) SHALL executar a checagem de lint e formatação do Ruff como primeiro passo do job de testes, utilizando anotações de erro integradas ao GitHub Actions.

#### Scenario: Pull Request com violações de código
- **WHEN** um Pull Request contiver arquivos com violações de regras do Ruff
- **THEN** o workflow deve falhar de forma rápida nas primeiras etapas, anotando visualmente os problemas no diff do PR e impedindo a execução demorada da suíte com interface gráfica (Xvfb).
