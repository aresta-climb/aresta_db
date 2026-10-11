# Spec Delta: Distribuição macOS

## MODIFIED Requirements

### Requirement: Verificação e Instalação de Atualizações via Sparkle e Cloudflare R2
A aplicação no macOS DEVE (SHALL) verificar no arranque e periodicamente a disponibilidade de novas versões através de feed XML (`appcast.xml`) hospedado no Cloudflare R2. Se houver versão superior marcada como crítica/obrigatória, o sistema DEVE interromper a inicialização na tela de abertura, indicar a necessidade de atualização e acionar o diálogo nativo do Sparkle Framework com validação criptográfica Ed25519.

#### Scenario: Detecção e instalação de atualização no macOS
- **WHEN** uma nova versão oficial do Editor Aresta for disponibilizada no feed `appcast.xml` do Cloudflare R2
- **THEN** o Sparkle Framework detecta a versão superior e exibe diálogo nativo informando o lançamento
- **AND** ao confirmar, o Sparkle realiza o download do `.dmg`, valida a assinatura Ed25519 e substitui o aplicativo em `/Applications`

#### Scenario: Detecção e bloqueio por atualização obrigatória no arranque
- **WHEN** o Editor Aresta for iniciado no macOS e o feed `appcast.xml` indicar versão superior com tag de atualização crítica
- **THEN** a verificação de plataforma retorna status de atualização obrigatória
- **AND** a tela de abertura bloqueia o avanço da inicialização e exibe mensagem amigável solicitando a atualização
- **AND** ao acionar a atualização, o Sparkle Framework abre o diálogo nativo impossibilitando adiamento ou pulo de versão

## ADDED Requirements

### Requirement: Suporte ao Cofre de Credenciais no Binário Empacotado do macOS
O executável compilado para macOS DEVE (SHALL) carregar e configurar o backend de chaveiro nativo Apple Keychain (`keyring.backends.macOS.Keyring`) em tempo de execução sem falhas por módulos ausentes.

#### Scenario: Inicialização do cofre de senhas no macOS empacotado
- **WHEN** o Editor Aresta for executado a partir do bundle `.app` compilado pelo PyInstaller
- **THEN** o módulo `keyring.backends.macOS` e os bindings de segurança do sistema estão disponíveis no pacote
- **AND** o adaptador de plataforma configura o backend macOS como cofre padrão com sucesso
