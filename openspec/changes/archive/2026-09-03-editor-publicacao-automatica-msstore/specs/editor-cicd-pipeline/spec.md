## ADDED Requirements

### Requirement: Publicação Automatizada de Pacote MSIX na Microsoft Store
O workflow de CI/CD de lançamento DEVE (SHALL) autenticar na API do Partner Center via MSStore CLI e publicar o pacote MSIX empacotado para o Store ID do aplicativo, permitindo ao operador escolher entre a submissão imediata para certificação ou o envio como rascunho.

#### Scenario: Disparo com publicação imediata (padrão)
- **WHEN** o workflow de lançamento for acionado com `should_publish: true` (ou omitido, assumindo padrão verdadeiro)
- **THEN** o sistema executa a publicação apontando para o binário `EditorAresta.msix` e o Store ID configurado
- **AND** submete a versão diretamente para a esteira de certificação da Microsoft Store

#### Scenario: Disparo em modo rascunho
- **WHEN** o workflow de lançamento for acionado com `should_publish: false`
- **THEN** o sistema anexa o parâmetro `--noCommit` à instrução de publicação do `msstore`
- **AND** disponibiliza o pacote no Partner Center em estado de rascunho sem iniciar a certificação imediatamente
