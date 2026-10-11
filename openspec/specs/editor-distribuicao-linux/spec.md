## Purpose

Define os requisitos de empacotamento, manifesto Flatpak e metadados AppStream para compilação e distribuição do Editor Aresta via repositório soberano OSTree no Cloudflare R2 e rede Flathub para distribuições Linux.

## Requirements

### Requirement: Manifesto Flatpak Oficial e Identificador de Aplicação
O repositório DEVE (SHALL) fornecer um manifesto Flatpak determinístico sob o identificador `com.arestaclimb.Editor` e arquivo de metadados AppStream (`com.arestaclimb.Editor.metainfo.xml`), utilizando `io.qt.PySide.BaseApp` e runtime `org.kde.Platform` para compilação nativa no Flathub sem intermediate de executável congelado por PyInstaller.

#### Scenario: Validação do manifesto Flatpak
- **WHEN** o manifesto `com.arestaclimb.Editor.yaml` for validado com ferramentas Flatpak
- **THEN** o arquivo declara `base: io.qt.PySide.BaseApp` e `runtime: org.kde.Platform`
- **AND** a execução do aplicativo invoca diretamente o interpretador Python (`python3 -m editor.main`) em `/app/bin/EditorAresta`
- **AND** os metadados AppStream incluem resumo em português, licença e categorias compatíveis com as lojas de aplicativos do Linux

### Requirement: Resolução Automática de Dependências Python para Flathub
O pipeline de distribuição Linux DEVE (SHALL) gerar a lista declarativa de fontes de dependências Python (`pypi-dependencies.json`) a partir do grupo `editor` do `pyproject.toml` exclusivamente durante o processo de compilação do repositório Flatpak com caching inteligente de downloads e módulos, suspendendo a sincronização com o repositório externo `aresta-editor-flathub`.

#### Scenario: Exportação de manifesto de dependências no CI
- **WHEN** o workflow de release do Linux for executado
- **THEN** as dependências do grupo `editor` são extraídas e convertidas pelo gerador Flatpak
- **AND** a compilação do Flatpak ocorre com cache ativo de downloads e módulos reutilizáveis
- **AND** a etapa de sincronização com o repositório `aresta-editor-flathub` permanece comentada e inativa

### Requirement: Formato Único de Distribuição Linux via Flatpak
O ecossistema Linux DEVE (SHALL) disponibilizar o Editor Aresta exclusivamente via repositório soberano Flatpak OSTree hospedado em Cloudflare R2 (`serving.arestaclimb.com/flatpak/repo`) e arquivo instalador `.flatpakref` com assinatura digital GPG, descontinuando o empacotamento de bundles offline `.flatpak` avulsos para assegurar que 100% dos usuários recebam atualizações automáticas contínuas.

#### Scenario: Geração de pacote instalável no Linux
- **WHEN** o processo de distribuição para Linux for finalizado
- **THEN** os artefatos de publicação gerados no R2 são o repositório OSTree (com static deltas e assinatura GPG), o arquivo `com.arestaclimb.Editor.flatpakref`, o arquivo `aresta.flatpakrepo` e o arquivo de controle `version.json`
- **AND** nenhum bundle offline `.flatpak` avulso deve ser gerado ou disponibilizado

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

### Requirement: Configuração de Ambiente do Subsistema Gráfico e Teclado Linux
A aplicação e o pacote Flatpak DEVEM (SHALL) configurar o ambiente de execução gráfico e de teclado para suprimir avisos não-críticos de parse de tabelas Compose externas do `libxkbcommon`.

#### Scenario: Supressão de Avisos Não-Críticos do libxkbcommon
- **WHEN** a aplicação for inicializada no Linux nativamente ou sob o Flatpak
- **THEN** a variável `XKB_LOG_LEVEL` deve estar configurada como `critical` antes da inicialização do contexto gráfico do Qt
- **AND** mensagens diagnósticas sobre teclas mortas ou símbolos desconhecidos não devem poluir a saída de erro da aplicação

### Requirement: Auto-Atualização e Verificação Remota Ativa no Linux
O subsistema de plataforma Linux (`AdaptadorLinux`) DEVE (SHALL) consultar ativamente na inicialização o endpoint de versão em `https://serving.arestaclimb.com/flatpak/version.json` e emitir o status de atualização correspondente para notificação visual imediata do usuário na interface de abertura.

#### Scenario: Detecção de atualização disponível no Linux
- **WHEN** a aplicação for inicializada no Linux e a versão em `version.json` for superior à versão local
- **THEN** o método de verificação de atualizações retorna `StatusAtualizacao.ATUALIZACAO_DISPONIVEL` ou `StatusAtualizacao.ATUALIZACAO_OBRIGATORIA`
- **AND** a Tela de Abertura exibe o aviso com ação de atualização para o usuário

#### Scenario: Aplicação na versão mais recente
- **WHEN** a aplicação for inicializada no Linux e a versão local for idêntica à versão em `version.json`
- **THEN** o método de verificação retorna `StatusAtualizacao.SEM_ATUALIZACAO`
- **AND** a aplicação segue normalmente para a seleção de croqui sem interrupções
