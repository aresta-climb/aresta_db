# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Sequenciamento e Atomicidade do Lançamento
O workflow DEVE (SHALL) realizar o corte oficial da versão (commit da versão de release, criação da tag `editor-v*` e incremento imediato para o próximo ciclo `-dev` na branch `main`) no job inicial `prepare_release` antes de disparar os jobs de compilação por plataforma, evitando colisão ou ambiguidade de versões caso a publicação conclua em um sistema operacional e falhe em outro; no Windows, DEVE executar e validar primeiro o canal Beta antes de compilar, validar e submeter à Microsoft Store.

#### Scenario: Corte prévio de versão antes dos builds multiplataforma
- **WHEN** o job `prepare_release` valida a suíte de testes e a campanha do Robô Caótico com sucesso
- **THEN** o workflow grava e envia o commit/tag `editor-v<versao>` e o commit do próximo ciclo `-dev` antes de iniciar `build_windows`, `build_macos` e `build_linux`.

#### Scenario: Sequenciamento com ambas as publicações ativas
- **WHEN** o workflow do Windows for acionado com `publicar_microsoft_store` igual a `true`
- **THEN** a compilação, smoke test pós-build e publicação do canal Beta no Cloudflare R2 ocorrem antes da compilação, smoke test pós-build e submissão oficial na Microsoft Store.
