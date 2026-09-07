## ADDED Requirements

### Requirement: Preservação e Exibição de Rastreamentos de Falhas na Compilação
O pipeline de compilação e deploy (`deploy_generated.py`) SHALL preservar o encadeamento causal de exceções capturadas e registrar o rastreamento completo (`traceback`) no registro de saída para exibição no painel de compilação e envio ao Sentry.

#### Scenario: Encadeamento de exceção de compilação
- **WHEN** ocorrer uma exceção não tratada ao compilar um croqui específico durante o deploy
- **THEN** a rotina de deploy SHALL registrar o rastreamento completo em `traceback.format_exc()` na saída do console E lançar o erro encadeando a exceção original via `raise ... from e`.

#### Scenario: Apresentação de rastreamento no painel de saída
- **WHEN** o deploy falhar e emitir linhas de rastreamento contendo referências de arquivo e pilha de chamadas
- **THEN** o painel de saída de compilação SHALL exibir essas linhas formatadas na cor correspondente a erros sem truncar o conteúdo.
