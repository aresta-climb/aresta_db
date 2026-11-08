# Spec Delta

## ADDED Requirements

### Requirement: Gate de Campanha do Robô Caótico Antes da Tag de Release
O job `prepare_release` do workflow `.github/workflows/release-editor.yml` SHALL executar a suíte de testes unitários/integração e uma campanha de 5 minutos do Robô Caótico **antes** de realizar o commit e a tag da versão de lançamento, reportando falhas inéditas ao Sentry e publicando as receitas JSON geradas como artefato do workflow em caso de falha.

#### Scenario: Bloqueio de lançamento quando o Robô Caótico encontra falha
- **WHEN** a campanha de 5 minutos do Robô Caótico no job `prepare_release` detecta ao menos uma falha de exceção ou violação de invariante
- **THEN** o passo SHALL enviar cada falha inédita ao Sentry com sua receita encolhida, fazer upload dos arquivos `.json` de `editor/caos/caminhos_regressao/` como artefato do GitHub Actions e falhar o job antes de criar o commit ou a tag `editor-v*`.
