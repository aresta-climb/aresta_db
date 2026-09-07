## MODIFIED Requirements

### Requirement: Publicação Automatizada de Pacote MSIX na Microsoft Store
O workflow de CI/CD de lançamento DEVE (SHALL) autenticar na API do Partner Center via MSStore CLI e publicar o pacote MSIX empacotado para o Store ID do aplicativo, operando por padrão em modo de rascunho (`--noCommit`) para validação prévia antes da submissão para certificação oficial.

#### Scenario: Disparo em modo rascunho (padrão)
- **WHEN** o workflow de lançamento for acionado com `should_publish: false` (ou omitido, assumindo falso por padrão)
- **THEN** o sistema anexa o parâmetro `--noCommit` à instrução de publicação do `msstore`
- **AND** disponibiliza o pacote no Partner Center em estado de rascunho sem iniciar a certificação imediatamente

#### Scenario: Disparo com submissão imediata para certificação
- **WHEN** o workflow de lançamento for acionado com `should_publish: true`
- **THEN** o sistema executa a publicação apontando para o binário `EditorAresta.msix` e o Store ID configurado
- **AND** submete a versão diretamente para a esteira de certificação da Microsoft Store

## ADDED Requirements

### Requirement: Orquestração de Compilação Dual e Distribuição Beta no Workflow de Lançamento
O workflow de lançamento DEVE (SHALL) compilar a versão oficial para a Microsoft Store e, em seguida, compilar, assinar digitalmente e distribuir a versão Beta no Cloudflare R2 com purgação de cache.

#### Scenario: Execução completa do workflow de lançamento dual
- **WHEN** o workflow de lançamento for disparado com uma versão oficial calculada
- **THEN** o pipeline compila o pacote de produção `EditorAresta.msix` e o envia para a Microsoft Store
- **AND** o pipeline compila a versão Beta com os recursos gráficos azuis e identidade `.Beta`
- **AND** assina o pacote `EditorArestaBeta.msix` utilizando a ferramenta `signtool` com o certificado configurado
- **AND** gera o arquivo `EditorAresta.appinstaller` e o envia juntamente com `EditorArestaBeta.msix` para o Cloudflare R2
- **AND** dispara a purgação do cache da Cloudflare para as URLs atualizadas
