# Proposta: Canal de Distribuição Beta via Windows App Installer e Cloudflare R2

## Por que

A esteira de publicação oficial na Microsoft Store exige revisão e certificação para cada nova versão lançada, gerando filas de espera de horas a dias e inviabilizando iterações rápidas de validação com testadores internos e beta testers. Para permitir validações frequentes e imediatas de novas funcionalidades sem abrir mão da segurança, isolamento e integridade do empacotamento Windows moderno, é necessário introduzir um canal de distribuição rápida baseado na tecnologia nativa Windows App Installer (`.appinstaller` + MSIX) hospedado no Cloudflare R2, convivendo em paralelo com o canal oficial da Microsoft Store.

## O que muda

- **Identidade e Tematização do Canal Beta**:
  - Introdução de identidade visual dedicada para versões de teste: ícones e tema em **Azul** (em contraste com o **Laranja** da versão de produção).
  - Tela de abertura (splash screen) contendo tarja textual e selo destacado **"BETA"**.
  - Nome da aplicação e título de todas as janelas exibindo `Editor Aresta (Beta)` acompanhado da numeração de versão.
  - Identidade explícita de processo na barra de tarefas do Windows (`AppUserModelID: aresta.editor.beta`) para garantir que o Windows não agrupe a versão Beta com a versão oficial da Loja.
  - Manifesto MSIX paralelo com `Name="ArestaClimbApps.EditorArestaClimb.Beta"` e `DisplayName="Editor Aresta (Beta)"`.
- **Distribuição Ágil via Windows App Installer (.appinstaller)**:
  - Geração automatizada do arquivo de controle `EditorAresta.appinstaller` apontando para `https://serving.arestaclimb.com/editor-beta/EditorArestaBeta.msix`.
  - Configuração de atualizações automáticas silenciosas a cada inicialização via Windows App Installer.
  - O binário no bucket R2 mantém nome estático (`EditorArestaBeta.msix`), eliminando acúmulo de binários históricos no armazenamento de objetos.
- **Instalador de Credencial Auto-contido (.bat amigável)**:
  - Criação do script `InstalarCertificadoEditorArestaBeta.bat` contendo a chave pública do certificado X.509 embutida em Base64 no próprio arquivo (extraída e importada nativamente via `certutil`).
  - Execução silenciosa em segundo plano (`-WindowStyle Hidden`), eliminando telas pretas de terminal para o testador.
  - Redirecionamento automático do navegador para a página de sucesso `https://arestaclimb.com/editor/beta/sucesso-certificado` após a importação.
- **Esteira de Lançamento Dual no CI/CD (`release-editor.yml`)**:
  - Compilação de produção: envia pacote `EditorAresta.msix` para o Microsoft Partner Center em modo rascunho (`--noCommit`) por padrão, pronto para promoção manual quando estabilizado.
  - Compilação beta: empacota e assina `EditorArestaBeta.msix` com chave digital da Aresta, gera `EditorAresta.appinstaller`, envia ambos para o Cloudflare R2 no prefixo `editor-beta/` e executa a purgação imediata de cache na CDN Cloudflare.

## Capacidades

### Novas Capacidades
- `editor-canal-beta`: Cobre a parametrização de canal de compilação (produção vs beta), tema e recursos gráficos azuis, splash screen com tarja BETA, título de janela com sufixo (Beta), `AppUserModelID` separado para a barra de tarefas do Windows e manifesto MSIX com identidade `.Beta`.
- `editor-distribuicao-appinstaller`: Cobre a especificação do manifesto `.appinstaller` com checagem automática de atualizações, script auto-contido de instalação de certificado (`.bat`) com execução oculta e redirecionamento web, rotina de envio para Cloudflare R2 e purgação de cache na Cloudflare.

### Capacidades Modificadas
- `editor-cicd-pipeline`: Modifica o fluxo de trabalho de lançamento do editor para orquestrar a compilação dual (Produção para rascunho na Microsoft Store e Beta para o R2 com `.appinstaller`), além de alterar o comportamento padrão de publicação imediata para modo rascunho (`should_publish: false` por padrão).

## Impacto

- **Repositório e Código do Editor**:
  - Novos recursos visuais azuis em `editor/recursos_beta/` e `editor/msix_beta/Assets/`.
  - Nova biblioteca independente `editor/core/configuracao_canal.py` com 100% de cobertura de testes unitários e de integração.
  - Ajuste em `editor/main.py` e `editor/views/tela_de_abertura.py` para utilizar a biblioteca de configuração de canal.
- **Infraestrutura e CI/CD**:
  - Fluxo de trabalho `.github/workflows/release-editor.yml` atualizado para compilação dual, assinatura via `signtool` e integração com Cloudflare R2 + Purge API.
  - Segredos configurados para o certificado de assinatura de código beta (`EDITOR_ARESTA_BETA_CERTIFICADO_PRIVADO_PFX`, `EDITOR_ARESTA_BETA_CERTIFICADO_PRIVADO_SENHA`).
  - Bucket `aresta-serving` passa a hospedar o prefixo `editor-beta/`.
- **Usuários e Testadores**:
  - Testadores podem manter as versões Oficial e Beta instaladas simultaneamente no mesmo Windows sem conflito de pacotes ou de dados locais.
