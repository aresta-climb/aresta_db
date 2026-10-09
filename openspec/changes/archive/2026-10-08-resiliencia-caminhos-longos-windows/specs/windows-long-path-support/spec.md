# Spec Delta

## MODIFIED Requirements

### Requirement: Habilitação de Caminhos Longos no Windows
A aplicação MUST declarar suporte a caminhos de arquivos maiores que 260 caracteres no sistema operacional Windows e garantir resiliência operacional em tempo de execução através da biblioteca `editor.plataforma` com caminhos estendidos e estruturas compactas de diretórios.

#### Scenario: Instalação via MSIX
- **WHEN** a aplicação for instalada e empacotada via MSIX
- **THEN** o manifesto do aplicativo DEVE conter a declaração `longPathAware` ativada, permitindo que a API do Windows ignore o limite MAX_PATH tradicional

#### Scenario: Normalização de caminhos para operações de I/O em disco no Windows
- **WHEN** rotinas de cópia e limpeza de arquivos (`copiar_imagens`, `copiar_anexos`, `force_rmtree`) forem executadas no deploy ou em operações de disco
- **THEN** os caminhos devem ser normalizados através de `editor.plataforma.normalizar_caminho_estendido()`, que no Windows prefixa caminhos absolutos com `\\?\` e em Linux/macOS retorna o caminho resolvido inalterado, permitindo manipular caminhos com mais de 260 caracteres mesmo se `LongPathsEnabled` estiver desativado no registro do sistema operacional

#### Scenario: Estrutura compacta de compilação no workspace experimental
- **WHEN** o `ExperimentalWorkspace` disparar a compilação local de um croqui
- **THEN** os artefatos compilados e suas imagens devem ser gerados diretamente na pasta `compilado/` sem aninhar uma subpasta redundante com o ID do croqui, economizando caracteres no caminho absoluto
