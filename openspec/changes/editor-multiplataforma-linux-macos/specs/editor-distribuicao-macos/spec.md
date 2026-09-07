## Purpose

Define os requisitos para empacotamento, assinatura digital Developer ID, notarização Apple e mecanismo de atualização automática in-app através do Sparkle Framework no macOS para a arquitetura Apple Silicon (ARM64).

## ADDED Requirements

### Requirement: Empacotamento de Bundle Nativo ARM64 e Imagem de Disco DMG
O sistema DEVE (SHALL) compilar o Editor Aresta como um bundle `.app` nativo para arquitetura ARM64 (`apple-silicon`) e gerar uma imagem de disco `.dmg` para distribuição direta aos usuários.

#### Scenario: Compilação de pacote no macOS
- **WHEN** o processo de build do macOS for executado em runner Apple Silicon
- **THEN** o PyInstaller gera a estrutura de bundle `EditorAresta.app` contendo o executável compilado para ARM64 e metadados `Info.plist`
- **AND** a ferramenta de empacotamento gera o arquivo de distribuição `EditorAresta.dmg`

### Requirement: Assinatura Digital e Notarização Apple para Gatekeeper
O executável e o instalador `.dmg` do macOS DEVEM (SHALL) ser assinados com um certificado oficial Apple *Developer ID Application* e aprovados pelo serviço de notarização automatizada da Apple (`xcrun notarytool`) com ticket grampeado (`stapler`).

#### Scenario: Notarização de artefato para Gatekeeper
- **WHEN** a imagem de disco `EditorAresta.dmg` for gerada no pipeline
- **THEN** todos os binários e bibliotecas internas são assinados com o certificado Apple configurado nos segredos
- **AND** o pacote é submetido ao serviço de notarização da Apple
- **AND** o ticket de aprovação é incorporado ao `.dmg` via `stapler`, permitindo abertura sem advertências de bloqueio de segurança

### Requirement: Verificação e Instalação de Atualizações via Sparkle e Cloudflare R2
A aplicação no macOS DEVE (SHALL) verificar periodicamente a disponibilidade de novas versões através de feed XML (`appcast.xml`) hospedado no Cloudflare R2 e permitir atualização in-app com validação criptográfica Ed25519.

#### Scenario: Detecção e instalação de atualização no macOS
- **WHEN** uma nova versão oficial do Editor Aresta for disponibilizada no feed `appcast.xml` do Cloudflare R2
- **THEN** o Sparkle Framework detecta a versão superior e exibe diálogo nativo informando o lançamento
- **AND** ao confirmar, o Sparkle realiza o download do `.dmg`, valida a assinatura Ed25519 e substitui o aplicativo em `/Applications`
