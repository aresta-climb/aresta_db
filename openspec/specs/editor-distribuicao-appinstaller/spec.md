# editor-distribuicao-appinstaller Specification

## Purpose
TBD - created by archiving change editor-canal-beta-appinstaller. Update Purpose after archive.
## Requirements
### Requirement: Geração do Manifesto Windows App Installer (.appinstaller)
O sistema DEVE (SHALL) fornecer uma ferramenta para gerar deterministicamente o arquivo de manifesto XML `EditorAresta.appinstaller` parametrizado com o número da versão e o URI de distribuição no Cloudflare R2.

#### Scenario: Geração do arquivo .appinstaller para nova versão
- **WHEN** o gerador for acionado informando a versão de lançamento (ex: `1.2.0.0`) e a URL base `https://serving.arestaclimb.com/editor-beta`
- **THEN** o arquivo XML gerado contém o elemento `<AppInstaller>` apontando para `https://serving.arestaclimb.com/editor-beta/EditorAresta.appinstaller`
- **AND** o elemento `<MainPackage>` declara `Name="ArestaClimbApps.EditorArestaClimb.Beta"`, `Version="1.2.0.0"` e `Uri="https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix"`
- **AND** o elemento `<UpdateSettings>` configura `<OnLaunch HoursBetweenUpdateChecks="0" />` e `<AutomaticBackgroundTask />` para atualização em segundo plano

### Requirement: Script Auto-Contido de Instalação de Certificado com Execução Oculta
O sistema DEVE (SHALL) gerar um script batch (`InstalarCertificadoEditorArestaBeta.bat`) contendo a chave pública do certificado de assinatura de testes embutida em Base64, que se auto-eleva com janela oculta, importa o certificado na loja `TrustedPeople` da máquina local e redireciona o navegador do usuário.

#### Scenario: Execução do script pelo usuário
- **WHEN** o usuário executa o script `InstalarCertificadoEditorArestaBeta.bat` no Windows
- **THEN** o script verifica se possui privilégios de Administrador
- **AND** caso não possua, relança o processo silenciosamente com elevação UAC utilizando `-WindowStyle Hidden`
- **AND** extrai e decodifica o bloco X.509 embutido via comando nativo `certutil -decode`
- **AND** adiciona o certificado à loja `TrustedPeople` da máquina local via `certutil -addstore`
- **AND** abre o navegador padrão na URL `https://arestaclimb.com/editor/beta/sucesso-certificado` sem manter janelas de prompt de comando visíveis

### Requirement: Sincronização com Cloudflare R2 e Purgação da CDN
O sistema DEVE (SHALL) fazer o upload dos artefatos estáticos do canal Beta para o bucket do Cloudflare R2 sob a rota `editor-beta/` e acionar a API da Cloudflare para purgar imediatamente o cache das URLs afetadas.

#### Scenario: Publicação e invalidação de cache do canal Beta
- **WHEN** os artefatos `EditorAresta.appinstaller` e `EditorArestaBeta.msix` forem gerados com sucesso
- **THEN** o sistema envia os arquivos para o bucket `aresta-serving` sob a chave `editor-beta/`
- **AND** dispara a requisição de purgação de cache para a zona Cloudflare configurada para as URLs `https://serving.arestaclimb.com/editor-beta/EditorAresta.appinstaller` e `https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix`

