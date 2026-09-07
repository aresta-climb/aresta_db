## Purpose

Define os requisitos para automação de empacotamento, compilação e lançamento do executável do Editor Aresta no pipeline de CI/CD.
## Requirements
### Requirement: Editor release automation
O sistema DEVE (SHALL) compilar e publicar o executável do editor mediante acionamento manual em um ambiente de dependências isolado, etiquetando a versão com a numeração semântica fornecida e garantindo que o tamanho do binário permaneça estritamente dentro dos limites de otimização (< 95MB).

#### Scenario: User triggers the workflow
- **WHEN** um mantenedor do repositório disparar o fluxo de trabalho de lançamento informando uma versão semântica válida
- **THEN** o sistema compila o executável para Windows utilizando o ambiente isolado do grupo `editor`, cria uma Release no GitHub anexada à nova tag do git, e faz o upload do arquivo `.exe` otimizado

### Requirement: Dev cycle progression
The system SHALL automatically bump the repository back to a development state after a successful release.

#### Scenario: Post-release bumping
- **WHEN** the release artifact has been uploaded and tagged successfully
- **THEN** the system calculates the next minor version, appends `-dev`, modifies the version file, and commits this back to the main branch

### Requirement: Completude da Suíte de Testes no Sparse Checkout do CI
O workflow de CI/CD DEVE (SHALL) incluir o diretório de testes arquiteturais e estáticos `tests/` no sparse-checkout dos jobs de teste de PR e de release.

#### Scenario: Execução da etapa de testes com sparse checkout
- **WHEN** o job de validação de PR ou de release é disparado com checkout otimizado (sparse-checkout)
- **THEN** o sistema baixa os diretórios de código e o diretório `tests/`
- **AND** executa 100% dos testes do repositório (incluindo tipagem estática e checagem AST)

### Requirement: Estabilidade e Rastreabilidade Sequencial no Runner de Lançamento Windows
O workflow de lançamento no Windows DEVE (SHALL) suprimir o bloqueio de relatórios de falha do Windows (WerFault.exe), executar a suíte de testes de forma sequencial com saída em tempo real não-bufferizada para diagnóstico inequívoco de travamentos, e encerrar o processo via chamada rápida de sistema operacional (`os._exit`) ao término para evitar falhas de desalocação nativa do Qt no Windows CRT.

#### Scenario: Diagnóstico inequívoco de travamento ou falha
- **WHEN** a etapa de testes do workflow de lançamento no Windows é iniciada
- **THEN** o sistema executa o pytest sequencialmente com `-n 0 -v -s` sob a flag de ambiente `CI: "true"`
- **AND** transmite a execução de cada teste imediatamente sem bufferização entre workers
- **AND** ao concluir, o pytest drena os recursos do Qt e encerra o processo via `os._exit` preservando o status de saída real sem disparar Access Violation no `Py_FinalizeEx`

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

### Requirement: Seleção Parametrizada do Tipo de Release no Workflow
O workflow de lançamento DEVE (SHALL) permitir ao operador selecionar o tipo de incremento de versão (`patch`, `minor`, `major` ou `custom`), calculando deterministicamente o número de versão semântico oficial a ser lançado antes das etapas de compilação e empacotamento.

#### Scenario: Operador seleciona incremento patch padrão
- **WHEN** o workflow for acionado com `bump_type: patch` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `0.2.1`

#### Scenario: Operador seleciona incremento minor
- **WHEN** o workflow for acionado com `bump_type: minor` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `0.3.0`

#### Scenario: Operador seleciona incremento major
- **WHEN** o workflow for acionado com `bump_type: major` e a versão do repositório for `0.2.1-dev`
- **THEN** o sistema calcula e utiliza a versão oficial `1.0.0`

#### Scenario: Operador fornece versão customizada válida
- **WHEN** o workflow for acionado com `bump_type: custom` e informar `custom_version: 0.5.0`
- **THEN** o sistema valida a conformidade SemVer e utiliza a versão `0.5.0` para o lançamento

### Requirement: Orquestração de Compilação Dual e Distribuição Beta no Workflow de Lançamento
O workflow de lançamento DEVE (SHALL) compilar a versão oficial para a Microsoft Store e, em seguida, compilar, assinar digitalmente e distribuir a versão Beta no Cloudflare R2 com purgação de cache.

#### Scenario: Execução completa do workflow de lançamento dual
- **WHEN** o workflow de lançamento for disparado com uma versão oficial calculada
- **THEN** o pipeline compila o pacote de produção `EditorAresta.msix` e o envia para a Microsoft Store
- **AND** o pipeline compila a versão Beta com os recursos gráficos azuis e identidade `.Beta`
- **AND** assina o pacote `EditorArestaBeta.msix` utilizando a ferramenta `signtool` com o certificado configurado
- **AND** gera o arquivo `EditorArestaBeta.appinstaller` e o envia juntamente com `EditorArestaBeta.msix` para o Cloudflare R2
- **AND** dispara a purgação do cache da Cloudflare para as URLs atualizadas

