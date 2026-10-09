# Spec Delta

## MODIFIED Requirements

### Requirement: Validações Pré-Envio e Resumo na Interface
O editor MUST validar a consistência técnica das alterações antes de disparar operações de rede e apresentar um resumo claro dos arquivos afetados no diálogo de publicação.

#### Scenario: Bloqueio de Envio com Erros de Compilação
- **WHEN** o croqui experimental contiver erros de compilação ou validação no `croqui.yaml` e o usuário acionar o envio de proposta
- **THEN** o sistema MUST solicitar confirmação explícita do usuário para enviar a proposta com erros para revisão colaborativa; caso cancelado, o envio é bloqueado, mas caso confirmado, o fluxo prossegue

#### Scenario: Detecção de Ausência de Modificações
- **WHEN** o estado do croqui experimental for idêntico à versão `upstream/main`
- **THEN** o sistema MUST informar que não há alterações a serem enviadas e encerrar o fluxo sem realizar push

#### Scenario: Resumo de Arquivos no Diálogo de Envio
- **WHEN** o diálogo de submissão for exibido
- **THEN** o diálogo MUST apresentar a contagem e a lista de arquivos a serem enviados (ex: `croqui.yaml` e imagens adicionadas/modificadas)
