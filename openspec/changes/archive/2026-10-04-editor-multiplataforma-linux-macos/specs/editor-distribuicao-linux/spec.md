## Purpose

Define os requisitos de empacotamento, manifesto Flatpak e metadados AppStream para compilação e distribuição do Editor Aresta na rede comunitária Flathub para distribuições Linux.

## ADDED Requirements

### Requirement: Manifesto Flatpak Oficial e Identificador de Aplicação
O repositório DEVE (SHALL) fornecer um manifesto Flatpak determinístico sob o identificador `com.arestaclimb.Editor` e arquivo de metadados AppStream (`com.arestaclimb.Editor.metainfo.xml`) para compilação na infraestrutura do Flathub.

#### Scenario: Validação do manifesto Flatpak
- **WHEN** o manifesto `com.arestaclimb.Editor.yaml` for validado com ferramentas Flatpak
- **THEN** o runtime declara as dependências gráficas e de execução do Qt/PySide6
- **AND** os metadados AppStream incluem resumo em português, licença e categorias compatíveis com as lojas de aplicativos do Linux

### Requirement: Integração com XDG Desktop Portals e Permissões do Sandbox
A aplicação empacotada em Flatpak DEVE (SHALL) utilizar os Portals do FreeDesktop para acesso nativo a diálogos de arquivos e rede local sem exigir privilégios globais irrestritos.

#### Scenario: Seleção de arquivos fora do sandbox
- **WHEN** o usuário seleciona um croqui ou diretório local do sistema de arquivos no Linux
- **THEN** o diálogo de arquivo é intermediado de forma transparente pelo XDG Desktop Portal
- **AND** a aplicação obtém acesso de leitura e escrita ao caminho selecionado
