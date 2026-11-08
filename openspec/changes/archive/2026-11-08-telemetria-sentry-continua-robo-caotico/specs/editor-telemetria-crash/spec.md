# Spec Delta

## MODIFIED Requirements

### Requirement: Envio de Receita do Robô Caótico no Contexto do Sentry
A biblioteca `editor/core/telemetria.py` SHALL manter o cliente Sentry continuamente ativo durante toda a campanha do Robô Caótico (registrando em tempo real os *breadcrumbs* de comandos do histórico e logs da aplicação) e, ao reportar uma falha inédita encontrada pelo robô, SHALL definir nível de severidade `fatal`, anexar o contexto estruturado `contexts.receita_robo_caotico` e anexar o arquivo `.json` da receita (`content_type="application/json"`) ao escopo do evento enviado ao Sentry.

#### Scenario: Captura de falha inédita encontrada pelo Robô Caótico
- **WHEN** o motor do Robô Caótico executa uma campanha com o envio ao Sentry habilitado e uma semente sofre uma falha inédita
- **THEN** o evento enviado ao Sentry SHALL conter o *stacktrace* real da exceção, todos os *breadcrumbs* cronológicos registrados durante os passos daquela semente até o momento da falha, `level="fatal"`, a tag `origem_crash="robo_caotico"`, o contexto estruturado `contexts.receita_robo_caotico` e o arquivo `.json` completo da receita anexado ao evento.
