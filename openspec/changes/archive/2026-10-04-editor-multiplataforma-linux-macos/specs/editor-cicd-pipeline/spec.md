## ADDED Requirements

### Requirement: Matriz Multiplataforma no Workflow de Lançamento
O workflow de lançamento de versão do Editor Aresta DEVE (SHALL) orquestrar a compilação do pacote macOS no runner Apple Silicon (`macos-14`), empacotando e assinando os artefatos em paralelo aos builds existentes do Windows.

#### Scenario: Execução de lançamento multiplataforma
- **WHEN** o workflow de lançamento for acionado com uma versão de lançamento calculada
- **THEN** o job do macOS executa no runner `macos-14`, compila o binário nativo ARM64, assina com o certificado Apple configurado e submete para notarização
- **AND** os artefatos de Windows continuam sendo compilados e publicados para a Microsoft Store e canal Beta

### Requirement: Publicação do Feed Sparkle e Artefatos macOS no Cloudflare R2
O pipeline de CI/CD DEVE (SHALL) fazer o upload do `.dmg` notarizado e do arquivo `appcast.xml` assinado com chave Ed25519 para o Cloudflare R2 sob a rota `editor/macos/`, disparando a purgação do cache da Cloudflare.

#### Scenario: Sincronização de nova versão do macOS no R2
- **WHEN** a imagem `EditorAresta.dmg` for aprovada na notarização da Apple
- **THEN** o workflow gera o `appcast.xml` assinado contendo o hash e a URL do novo pacote
- **AND** envia ambos os arquivos para o bucket `aresta-serving` sob a chave `editor/macos/`
- **AND** solicita a purgação de cache das URLs atualizadas
