# Spec Delta

## MODIFIED Requirements

### Requirement: Integração com XDG Desktop Portals e Permissões do Sandbox
A aplicação empacotada em Flatpak DEVE (SHALL) utilizar os Portals do FreeDesktop para acesso nativo a diálogos de arquivos, rede local e armazenamento seguro de credenciais, sem exigir privilégios globais irrestritos ou acesso direto aos serviços D-Bus legados de senhas do host (`org.freedesktop.secrets` e `org.kde.kwalletd*`).

#### Scenario: Seleção de arquivos fora do sandbox
- **WHEN** o usuário seleciona um croqui ou diretório local do sistema de arquivos no Linux
- **THEN** o diálogo de arquivo é intermediado de forma transparente pelo XDG Desktop Portal
- **AND** a aplicação obtém acesso de leitura e escrita ao caminho selecionado

#### Scenario: Armazenamento seguro de credenciais sem brechas no sandbox
- **WHEN** a aplicação Flatpak armazena ou recupera a sessão do usuário
- **THEN** a chave mestre é obtida via interface segura `org.freedesktop.portal.Secret`
- **AND** o manifesto Flatpak não declara permissões `--talk-name=org.freedesktop.secrets` nem `--talk-name=org.kde.kwalletd*`
- **AND** os dados confidenciais são armazenados criptografados com AES-256-GCM no diretório de dados isolado da aplicação
