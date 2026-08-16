## ADDED Requirements

### Requirement: Canonical Self-Installation
The system SHALL detectar sua execução fora do diretório canônico (AppData) e migrar sua instância de forma autônoma.

#### Scenario: Running from a random directory
- **WHEN** a aplicação é executada a partir de uma pasta qualquer (ex: Downloads)
- **THEN** o sistema copia a si mesmo para `%LOCALAPPDATA%\EditorAresta\`, substitui o arquivo original por um atalho `.lnk`, cria o recibo `cleanup_folder.txt` e reinicia do local oficial.

### Requirement: Restrictive Garbage Collection
The system SHALL limpar instâncias obsoletas (`EditorAresta.old.exe`) sob restrições rígidas de nome de arquivo para prevenir exclusões arbitrárias.

#### Scenario: App boots up after an update
- **WHEN** a aplicação inicia sua rotina
- **THEN** ela exclui o lixo `.old.exe` da sua própria pasta e da pasta explicitada no `cleanup_folder.txt` (ignorando qualquer outra parte do texto maliciosa do recibo), finalizando com a destruição do recibo.
