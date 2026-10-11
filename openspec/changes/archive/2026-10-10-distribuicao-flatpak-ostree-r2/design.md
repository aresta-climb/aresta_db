# Design: Distribuição Soberana do Editor Aresta via Repositório OSTree (Flatpak) no Cloudflare R2

## Context

O Editor Aresta atualmente compila um bundle `.flatpak` offline e sincroniza um repositório git intermediário (`aresta-editor-flathub`) visando a publicação no Flathub. Como a submissão inicial enfrenta bloqueios por gatekeeping, o projeto precisa de um canal soberano de distribuição no Linux. A infraestrutura existente já conta com o Cloudflare R2 servindo o domínio `serving.arestaclimb.com` para artefatos do macOS e web, com credenciais S3 e purge de cache configurados no GitHub Actions.

## Goals / Non-Goals

**Goals:**
- Publicar um repositório Flatpak OSTree soberano em `https://serving.arestaclimb.com/flatpak/repo/` assinado com chave GPG oficial.
- Gerar deltas estáticos (`static deltas`) entre versões consecutivas para que atualizações consumam apenas kilobytes/poucos megabytes.
- Fornecer instalador de 1 clique (`com.arestaclimb.Editor.flatpakref`) com `RuntimeRepo` apontado para o Flathub para resolução transparente de runtimes sem hospedar o SDK do KDE no R2.
- Implementar verificação ativa de versão remota no `AdaptadorLinux` via `version.json`, integrando com a `TelaDeAbertura` para alertar sobre novas versões disponíveis ou mandatórias.
- Habilitar caching inteligente no CI (`flatpak-builder@v6` com `cache: true` e `build-bundle: false`) para reduzir o tempo de compilação.
- Tratar o bootstrap do repositório no CI de forma determinística (sem supressão de erros via `|| true`).
- Manter política de `Cache-Control` uniforme no R2, confiando estritamente na API de purge de cache da Cloudflare para os metadados mutáveis.

**Non-Goals:**
- Não gerar ou publicar bundles avulsos offline `.flatpak`, garantindo que todo usuário Linux esteja vinculado ao canal de atualização contínua.
- Não manter sincronização ativa com o Flathub enquanto a revisão inicial estiver suspensa (código permanece comentado no CI).
- Não re-hospedar runtimes do KDE ou PySide no Cloudflare R2.

## Decisions

### 1. Repositório OSTree Estático em Modo `archive-z2` no Cloudflare R2
- **Decisão**: Utilizar o repositório OSTree no modo `archive-z2` (arquivos comprimidos estáticos compatíveis com HTTP/S3).
- **Racional**: Permite que o Cloudflare R2 funcione como um mirror Flatpak completo com custo zero de egress e alta performance global.
- **Alternativas consideradas**:
  - *Distribuir apenas bundles `.flatpak`*: Descartado porque impede atualizações automáticas via `flatpak update` e gasta 80 MB por download.
  - *Servidor dedicado de flatpak (ex: flat-manager)*: Descartado por complexidade operacional desnecessária; OSTree estático no R2 não requer servidores ativos.

### 2. Assinatura Digital GPG no CI
- **Decisão**: Assinar digitalmente os commits e o arquivo `summary` do repositório OSTree com chave GPG oficial (`flatpak build-update-repo --generate-static-deltas --gpg-sign=...`). A chave pública é exportada em base64 e embutida no `.flatpakref` e `.flatpakrepo`.
- **Racional**: Elimina avisos de segurança nas lojas de aplicativos do Linux (GNOME Software e KDE Discover) e previne adulteração.
- **Alternativas consideradas**:
  - *Repositório não assinado (`gpg-verify=false`)*: Descartado por degradar a confiança e exigir confirmação explícita do usuário no terminal.

### 3. Eliminação do Mascaramento de Erros (`|| true`) e Bootstrap Seguro
- **Decisão**: O script de sincronização no CI verifica explicitamente via HTTP HEAD se `https://serving.arestaclimb.com/flatpak/repo/summary` existe antes de executar comandos OSTree:
  - Se HTTP 200: Executa obrigatoriamente `ostree pull --mirror` da versão anterior para permitir o cálculo de deltas binários. Se falhar, interrompe o CI.
  - Se HTTP 404: Inicializa o repositório limpo (`ostree init --mode=archive-z2`).
  - Qualquer outro código: Falha o build imediatamente.
- **Racional**: Garante confiabilidade operacional, impedindo que falhas de rede ou autenticação gerem estados órfãos silenciosamente.

### 4. Cache-Control Uniforme com Invalidação Cirúrgica via Purge API
- **Decisão**: Todos os arquivos enviados ao R2 recebem o cabeçalho padrão de cache longo (1 ano / immutable). Apenas os arquivos de metadados mutáveis são invalidados via API `purge_cache` da Cloudflare ao final do deploy:
  - `https://serving.arestaclimb.com/flatpak/repo/summary`
  - `https://serving.arestaclimb.com/flatpak/repo/summary.sig`
  - `https://serving.arestaclimb.com/flatpak/version.json`
  - `https://serving.arestaclimb.com/flatpak/com.arestaclimb.Editor.flatpakref`
  - `https://serving.arestaclimb.com/flatpak/aresta.flatpakrepo`
- **Racional**: Atende à infraestrutura da Cloudflare sem complexidade de regras de cabeçalho por arquivo no cliente S3.

### 5. Caching do Flatpak Builder no GitHub Actions
- **Decisão**: Configurar `flatpak/flatpak-github-actions/flatpak-builder@v6` com `cache: true` e `build-bundle: false`.
- **Racional**: O `flatpak-builder` armazena downloads por hash SHA256 em `.flatpak-builder/downloads/` e módulos compilados em `.flatpak-builder/cache/`. Quando apenas o código do Aresta é alterado, o módulo de dependências pip é restaurado do cache sem compilação, reduzindo o tempo de build de minutos para segundos.

### 6. Verificação Ativa de Atualizações no `AdaptadorLinux`
- **Decisão**: O método `AdaptadorLinux.verificar_atualizacoes_disponiveis()` faz uma requisição HTTP leve para `https://serving.arestaclimb.com/flatpak/version.json`. Se a versão remota for superior à versão local em `editor.core.version.VERSION`, retorna `ResultadoAtualizacao` com status correspondente (`ATUALIZACAO_DISPONIVEL` ou `ATUALIZACAO_OBRIGATORIA`), acionando o botão e aviso na `TelaDeAbertura`.
- **Racional**: Não depende da passividade do usuário ou da rotina do sistema operacional para avisar que há um release crítico disponível.

### 7. Modularização Library-First (`editor/release_tools/publicar_flatpak_r2.py`)
- **Decisão**: Toda a lógica de verificação remota, upload para o R2 e chamada de purge de cache será encapsulada em uma biblioteca autônoma em `editor/release_tools/`, acompanhada de seu respectivo arquivo `_test.py` com 100% de cobertura.

## Risks / Trade-offs

- **[Risco] Usuário sem Flathub configurado não consegue baixar o runtime do KDE** → **Mitigação**: O arquivo `com.arestaclimb.Editor.flatpakref` declara `RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo`. O Flatpak baixa o runtime automaticamente do Flathub público sem exigir que o Aresta esteja listado lá.
- **[Risco] Latência na primeira execução sem cache no CI** → **Mitigação**: O workflow usa cache automático do `flatpak-builder@v6`; apenas a primeira execução do runner frio baixa os wheels do PySide6.
- **[Risco] Chave GPG expirada ou perdida** → **Mitigação**: Gerar chave sem data de expiração mandatória para este remote, com backup seguro nos Secrets da organização.
