# editor-canal-beta Specification

## Purpose
TBD - created by archiving change editor-canal-beta-appinstaller. Update Purpose after archive.
## Requirements
### Requirement: Parametrização e Identificação do Canal de Lançamento
O sistema DEVE (SHALL) fornecer uma biblioteca de configuração de canal (`configuracao_canal`) que identifica deterministicamente se a aplicação está operando em modo oficial de produção ou em modo de teste Beta.

#### Scenario: Detecção do canal padrão de produção
- **WHEN** a variável de ambiente `ARESTA_CANAL` não estiver definida ou possuir o valor `producao`
- **THEN** o sistema define o canal como produção
- **AND** o nome da aplicação é configurado como `Editor Aresta`
- **AND** o identificador de processo do Windows (AppUserModelID) é definido como `aresta.editor.v1`

#### Scenario: Detecção do canal Beta
- **WHEN** a variável de ambiente `ARESTA_CANAL` estiver definida com o valor `beta`
- **THEN** o sistema define o canal como beta
- **AND** o nome da aplicação é configurado como `Editor Aresta (Beta)`
- **AND** o identificador de processo do Windows (AppUserModelID) é definido como `aresta.editor.beta`

### Requirement: Identidade Visual e Tematização do Canal Beta
A aplicação no canal Beta DEVE (SHALL) carregar elementos gráficos específicos em tonalidade azul com indicação textual explícita de ambiente Beta na tela de abertura (splash screen) e nas janelas do sistema.

#### Scenario: Exibição da tela de abertura no canal Beta
- **WHEN** a aplicação é inicializada no canal Beta
- **THEN** a tela de abertura carrega a logo azul contendo o selo textual `BETA`
- **AND** o título da janela exibe o nome `Editor Aresta (Beta)` acompanhado da numeração da versão

#### Scenario: Isolamento da barra de tarefas do Windows
- **WHEN** a aplicação é executada no canal Beta em uma máquina que já possui a versão oficial aberta ou instalada
- **THEN** o sistema operacional Windows registra o processo sob o identificador `aresta.editor.beta`
- **AND** a janela da aplicação não é agrupada com a janela da versão de produção na barra de tarefas

### Requirement: Manifesto MSIX com Identidade de Pacote Isolada
O pacote MSIX do canal Beta DEVE (SHALL) possuir um manifesto `AppxManifest.xml` com identidade e nome de exibição dedicados para permitir a instalação simultânea com o pacote da Microsoft Store.

#### Scenario: Validação do manifesto MSIX do canal Beta
- **WHEN** o manifesto MSIX para o canal Beta for inspecionado
- **THEN** a tag `<Identity>` possui o atributo `Name="ArestaClimbApps.EditorArestaClimb.Beta"`
- **AND** a tag `<DisplayName>` possui o valor `Editor Aresta (Beta)`

