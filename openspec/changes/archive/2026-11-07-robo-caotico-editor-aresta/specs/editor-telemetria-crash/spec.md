# Spec Delta

## ADDED Requirements

### Requirement: Envio de Receita do Robô Caótico no Contexto do Sentry
A biblioteca `editor/core/telemetria.py` SHALL permitir anexar contextos estruturados adicionais (como `contexts.receita_robo_caotico`) e definir nível de severidade `fatal` ao reportar uma exceção ao Sentry, preservando os breadcrumbs normais da aplicação e a sanitização de caminhos locais.

#### Scenario: Captura de falha inédita encontrada pelo Robô Caótico
- **WHEN** o motor do Robô Caótico encontra uma falha inédita com o envio ao Sentry habilitado e invoca a captura passando o dicionário `receita_robo_caotico`
- **THEN** o evento enviado ao Sentry SHALL conter `level="fatal"`, a tag `origem_crash="robo_caotico"`, o contexto estruturado `contexts.receita_robo_caotico` (com `seed`, `dataset`, `passos_minimos` e `passos_originais`) e todos os breadcrumbs cronológicos registrados até o momento da falha.

### Requirement: Diagnóstico e Reprodução de Receitas do Editor via MCP Sentry
A skill `diagnosticar-issue-sentry` SHALL documentar o fluxo de extração de `contexts.receita_robo_caotico` para issues do `aresta_db`, orientando o salvamento da receita em `editor/caos/caminhos_regressao/` e sua execução via `pytest editor/caos/regressao_caminhos_test.py`.

#### Scenario: Reprodução de issue do Editor Aresta gerada pelo Robô Caótico
- **WHEN** um agente investiga uma Issue do GitHub do `aresta_db` vinculada a um evento do Sentry que possui `contexts.receita_robo_caotico`
- **THEN** o agente SHALL salvar o JSON da receita em `editor/caos/caminhos_regressao/issue_<NUMERO>_seed_<SEED>.json` e reproduzir a falha executando `uv run pytest editor/caos/regressao_caminhos_test.py` antes de aplicar a correção.
