# editor-workflow-release Specification

## Purpose

Define os requisitos e o comportamento esperado do workflow de lançamento do Editor Aresta, assegurando publicação ágil focada no canal Beta por padrão e submissão direta para certificação na Microsoft Store quando requisitado.

## Requirements

### Requirement: Publicação Padrão no Canal Beta
O workflow de lançamento do Editor Aresta DEVE (SHALL) publicar automaticamente os artefatos compilados e assinados no canal Beta (Cloudflare R2 e AppInstaller), executando uma única compilação PyInstaller quando o parâmetro da Microsoft Store não estiver habilitado.

#### Scenario: Execução padrão do workflow com foco exclusivo em Beta
- **WHEN** o workflow de lançamento for acionado sem marcar a opção `publicar_microsoft_store` (ou com valor `false`)
- **THEN** o sistema executa a compilação exclusiva do canal Beta e publica os artefatos no Cloudflare R2
- **AND** o sistema pula integralmente as etapas de compilação, empacotamento e upload para a Microsoft Store.

### Requirement: Lançamento e Submissão Direta na Microsoft Store
O workflow de lançamento do Editor Aresta DEVE (SHALL) disponibilizar o parâmetro booleano `publicar_microsoft_store` (com valor padrão `true`) que, quando habilitado, aciona a compilação do executável de produção, empacotamento MSIX e submissão direta para certificação na Microsoft Store sem a flag `--noCommit`.

#### Scenario: Execução com lançamento na Microsoft Store ativado
- **WHEN** o workflow de lançamento for disparado com o parâmetro `publicar_microsoft_store` preenchido como `true`
- **THEN** o sistema executa o fluxo do canal Beta com sucesso
- **AND** em seguida compila o executável oficial de produção e gera o pacote MSIX oficial
- **AND** executa a ferramenta `msstore` para publicação sem a opção `--noCommit`, submetendo a atualização imediatamente para revisão e certificação.

#### Scenario: Ausência de submissão em modo rascunho
- **WHEN** qualquer publicação para a Microsoft Store for disparada pelo workflow
- **THEN** o comando executado com `msstore` não inclui o argumento `--noCommit`
- **AND** a submissão não permanece pendente como rascunho manual no painel do Microsoft Partner Center.

### Requirement: Sequenciamento e Atomicidade do Lançamento
O workflow DEVE (SHALL) realizar o corte oficial da versão (commit da versão de release, criação da tag `editor-v*` e incremento imediato para o próximo ciclo `-dev` na branch `main`) no job inicial `prepare_release` antes de disparar os jobs de compilação por plataforma, evitando colisão ou ambiguidade de versões caso a publicação conclua em um sistema operacional e falhe em outro; no Windows, DEVE executar e validar primeiro o canal Beta antes de compilar, validar e submeter à Microsoft Store.

#### Scenario: Corte prévio de versão antes dos builds multiplataforma
- **WHEN** o job `prepare_release` valida a suíte de testes e a campanha do Robô Caótico com sucesso
- **THEN** o workflow grava e envia o commit/tag `editor-v<versao>` e o commit do próximo ciclo `-dev` antes de iniciar `build_windows`, `build_macos` e `build_linux`.

#### Scenario: Sequenciamento com ambas as publicações ativas
- **WHEN** o workflow do Windows for acionado com `publicar_microsoft_store` igual a `true`
- **THEN** a compilação, smoke test pós-build e publicação do canal Beta no Cloudflare R2 ocorrem antes da compilação, smoke test pós-build e submissão oficial na Microsoft Store.

### Requirement: Gate de Campanha do Robô Caótico Antes da Tag de Release
O job `prepare_release` do workflow `.github/workflows/release-editor.yml` SHALL executar a suíte de testes unitários/integração e uma campanha de 5 minutos do Robô Caótico **antes** de realizar o commit e a tag da versão de lançamento, reportando falhas inéditas ao Sentry e publicando as receitas JSON geradas como artefato do workflow em caso de falha.

#### Scenario: Bloqueio de lançamento quando o Robô Caótico encontra falha
- **WHEN** a campanha de 5 minutos do Robô Caótico no job `prepare_release` detecta ao menos uma falha de exceção ou violação de invariante
- **THEN** o passo SHALL enviar cada falha inédita ao Sentry com sua receita encolhida, fazer upload dos arquivos `.json` de `editor/caos/caminhos_regressao/` como artefato do GitHub Actions e falhar o job antes de criar o commit ou a tag `editor-v*`.

### Requirement: Gate Obrigatório de Smoke Test Pós-Build Offline Antes da Publicação
Os workflows de compilação e distribuição de cada sistema operacional (Windows, macOS Apple Silicon, macOS Intel e Linux Flatpak) DEVEM (SHALL) executar um smoke test ponta a ponta offline contra o artefato compilado real antes de realizar qualquer upload ou publicação em canais externos (Cloudflare R2, feed Sparkle ou Microsoft Store).

#### Scenario: Validação pós-build no Windows antes de publicar Beta e Microsoft Store
- **WHEN** o workflow de build do Windows conclui a geração do pacote `onedir` via PyInstaller (tanto no canal Beta quanto no canal Produção da Microsoft Store)
- **THEN** o workflow SHALL executar o smoke test offline sobre `EditorAresta.exe` gerado
- **AND** SHALL abortar imediatamente antes da assinatura/publicação no Cloudflare R2 ou submissão à Microsoft Store caso o código de saída não seja `0`.

#### Scenario: Validação pós-build no macOS Apple Silicon e Intel via Rosetta 2
- **WHEN** a matriz de build do macOS monta o bundle `EditorAresta.app` para `arm64` (Apple Silicon) e `x86_64` (Intel)
- **THEN** o workflow SHALL verificar que o binário principal Mach-O corresponde à arquitetura alvo da matriz (`arm64` ou `x86_64`)
- **AND** SHALL executar o smoke test offline diretamente em `arm64` nativo e via `arch -x86_64` sob Rosetta 2 na variante Intel antes de disponibilizar o `.dmg` para publicação no Cloudflare R2 e feed Sparkle.

#### Scenario: Validação pós-build no Linux Flatpak antes de publicar no R2
- **WHEN** o workflow de build do Linux conclui a compilação do pacote Flatpak
- **THEN** o workflow SHALL executar o smoke test offline utilizando o ambiente Flatpak compilado (`QT_QPA_PLATFORM=offscreen`) antes de publicar o repositório OSTree no Cloudflare R2.
