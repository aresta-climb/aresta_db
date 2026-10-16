# Spec Delta: Distribuição macOS Multi-Arquitetura (Apple Silicon e Intel)

## ADDED Requirements

### Requirement: Empacotamento de Bundle Nativo Intel x86_64 e Imagem de Disco DMG
O sistema DEVE (SHALL) compilar o Editor Aresta como um bundle `.app` nativo para arquitetura Intel (`x86_64`) e gerar uma imagem de disco `.dmg` para distribuição direta aos usuários de Macs com processadores Intel.

#### Scenario: Compilação de pacote no macOS para Intel
- **WHEN** o processo de build do macOS for executado em runner Intel (`macos-13`)
- **THEN** o PyInstaller gera a estrutura de bundle `EditorAresta.app` contendo o executável compilado para x86_64 e metadados `Info.plist`
- **AND** a ferramenta de empacotamento gera o arquivo de distribuição `EditorAresta-<versao>-intel.dmg` e alias `EditorAresta-intel-latest.dmg`

## MODIFIED Requirements

### Requirement: Assinatura Digital e Notarização Apple para Gatekeeper
O executável e o instalador `.dmg` do macOS para Apple Silicon e Intel DEVEM (SHALL) ser assinados com um certificado oficial Apple *Developer ID Application* e aprovados pelo serviço de notarização automatizada da Apple (`xcrun notarytool`) com ticket grampeado (`stapler`).

#### Scenario: Notarização de artefato para Gatekeeper
- **WHEN** a imagem de disco `EditorAresta.dmg` (ou `EditorAresta-<versao>-<arch>.dmg`) for gerada no pipeline
- **THEN** todos os binários e bibliotecas internas são assinados com o certificado Apple configurado nos segredos
- **AND** o pacote é submetido ao serviço de notarização da Apple
- **AND** o ticket de aprovação é incorporado ao `.dmg` via `stapler`, permitindo abertura sem advertências de bloqueio de segurança tanto em Apple Silicon quanto em Intel

### Requirement: Verificação e Instalação de Atualizações via Sparkle e Cloudflare R2
A aplicação no macOS DEVE (SHALL) verificar no arranque e periodicamente a disponibilidade de novas versões através de feed XML (`appcast.xml`) hospedado no Cloudflare R2. O feed DEVE fornecer itens independentes para as arquiteturas `arm64` e `x86_64` com a diretiva `<sparkle:hardwareRequirements>`, garantindo que cada máquina baixe a versão compatível com seu processador com validação criptográfica Ed25519. Se houver versão superior marcada como crítica/obrigatória, o sistema DEVE interromper a inicialização na tela de abertura, indicar a necessidade de atualização e acionar o diálogo nativo do Sparkle Framework com validação criptográfica Ed25519.

#### Scenario: Detecção e instalação de atualização no macOS
- **WHEN** uma nova versão oficial do Editor Aresta for disponibilizada no feed `appcast.xml` do Cloudflare R2
- **THEN** o Sparkle Framework detecta a versão superior, seleciona o item compatível com a arquitetura do hardware em execução (`arm64` ou `x86_64`) e exibe diálogo nativo informando o lançamento
- **AND** ao confirmar, o Sparkle realiza o download do `.dmg` correspondente, valida a assinatura Ed25519 e substitui o aplicativo em `/Applications`

#### Scenario: Detecção e bloqueio por atualização obrigatória no arranque
- **WHEN** o Editor Aresta for iniciado no macOS e o feed `appcast.xml` indicar versão superior com tag de atualização crítica
- **THEN** a verificação de plataforma retorna status de atualização obrigatória
- **AND** a tela de abertura bloqueia o avanço da inicialização e exibe mensagem amigável solicitando a atualização
- **AND** ao acionar a atualização, o Sparkle Framework abre o diálogo nativo impossibilitando adiamento ou pulo de versão
