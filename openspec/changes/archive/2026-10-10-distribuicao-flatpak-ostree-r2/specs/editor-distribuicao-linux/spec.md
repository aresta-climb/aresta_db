# Spec Delta: editor-distribuicao-linux

## MODIFIED Requirements

### Requirement: Formato Único de Distribuição Linux via Flatpak
O ecossistema Linux DEVE (SHALL) disponibilizar o Editor Aresta exclusivamente via repositório soberano Flatpak OSTree hospedado em Cloudflare R2 (`serving.arestaclimb.com/flatpak/repo`) e arquivo instalador `.flatpakref` com assinatura digital GPG, descontinuando o empacotamento de bundles offline `.flatpak` avulsos para assegurar que 100% dos usuários recebam atualizações automáticas contínuas.

#### Scenario: Geração de pacote instalável no Linux
- **WHEN** o processo de distribuição para Linux for finalizado
- **THEN** os artefatos de publicação gerados no R2 são o repositório OSTree (com static deltas e assinatura GPG), o arquivo `com.arestaclimb.Editor.flatpakref`, o arquivo `aresta.flatpakrepo` e o arquivo de controle `version.json`
- **AND** nenhum bundle offline `.flatpak` avulso deve ser gerado ou disponibilizado

### Requirement: Resolução Automática de Dependências Python para Flathub
O pipeline de distribuição Linux DEVE (SHALL) gerar a lista declarativa de fontes de dependências Python (`pypi-dependencies.json`) a partir do grupo `editor` do `pyproject.toml` exclusivamente durante o processo de compilação do repositório Flatpak com caching inteligente de downloads e módulos, suspendendo a sincronização com o repositório externo `aresta-editor-flathub`.

#### Scenario: Exportação de manifesto de dependências no CI
- **WHEN** o workflow de release do Linux for executado
- **THEN** as dependências do grupo `editor` são extraídas e convertidas pelo gerador Flatpak
- **AND** a compilação do Flatpak ocorre com cache ativo de downloads e módulos reutilizáveis
- **AND** a etapa de sincronização com o repositório `aresta-editor-flathub` permanece comentada e inativa

## ADDED Requirements

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
