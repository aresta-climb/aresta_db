# Especificação: Infraestrutura de Tipagem Estática

## Requirements

### Requirement: Configuração Estrita do MyPy no pyproject.toml
O projeto SHALL declarar dependências de tipagem estática no grupo `dev` do `pyproject.toml` e configurar a seção `[tool.mypy]` com modo estrito (`strict = true`, `disallow_untyped_defs = true`, `no_implicit_optional = true`, `warn_return_any = true`).

#### Scenario: Instalação e verificação de configuração estrita
- **WHEN** as dependências do grupo `dev` forem instaladas via `uv`
- **THEN** o utilitário `mypy` deve estar disponível e ler as regras estritas da seção `[tool.mypy]` do `pyproject.toml`.

### Requirement: Teste Guardião de Tipagem no Pytest
O sistema SHALL fornecer um módulo de testes de conformidade de tipos integrado à suíte do `pytest`, que invoca o `mypy` programaticamente e valida que os arquivos configurados não contêm violações de tipos.

#### Scenario: Execução bem-sucedida do teste quando os tipos estão válidos
- **WHEN** o `pytest` executa o teste de tipagem estática sobre arquivos em conformidade
- **THEN** o teste passa com código de saída 0 e sem erros reportados.

#### Scenario: Falha do teste ao detectar código com erro de tipo
- **WHEN** uma função com tipo incorreto ou retorno incompatível for analisada
- **THEN** o teste do `pytest` falha e exibe a mensagem detalhada com o arquivo, linha e código do erro.

### Requirement: Metateste de Inspeção de Assinaturas e Retornos via AST
O sistema SHALL implementar um teste baseado na árvore sintática abstrata (AST) que verifica se funções e métodos possuem anotações de parâmetros e anotação de tipo de retorno explícitas.

#### Scenario: Detecção de função sem anotações de tipo
- **WHEN** uma função ou método é declarado sem anotações de parâmetros ou sem tipo de retorno
- **THEN** o metateste de AST falha apontando o nome do arquivo, linha e assinatura incompleta.
