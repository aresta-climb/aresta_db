# Design: Distribuição Multi-Arquitetura do Editor macOS (Apple Silicon e Intel)

## Context

O Editor Aresta para macOS é empacotado via PyInstaller (`onedir`) e encapsulado em imagem de disco `.dmg` com assinatura Apple Developer ID e notarização oficial. Até então, o workflow era executado unicamente no runner `macos-14` (Apple Silicon M1, `arm64`).

Tentativas de gerar um fat binary único (`universal2`) via PyInstaller esbarram no fato de que dependências cruciais em C/C++ (`pillow`, `pygit2`, `pillow-heif`, `cryptography`) distribuem wheels separadas por arquitetura no PyPI, e ferramentas de mesclagem como `lipo` corrompem os pacotes do PyInstaller. A solução estabelecida no mercado para ecossistemas Python/Qt no macOS é a distribuição segregada de imagens `.dmg` para Apple Silicon e Intel.

## Goals / Non-Goals

**Goals:**
- Configurar matriz de compilação no GitHub Actions executando em hardware nativo: `macos-14` (ARM64) e `macos-13` (Intel x86_64).
- Gerar, assinar e notarizar independentemente os pacotes `.dmg` para cada arquitetura.
- Publicar no Cloudflare R2 os arquivos versionados e latest de cada arquitetura, mantendo `EditorAresta-latest.dmg` apontando para a versão Apple Silicon por compatibilidade.
- Gerar um feed Sparkle (`appcast.xml`) unificado contendo itens diferenciados por `<sparkle:hardwareRequirements>`.
- Apresentar na página do Editor (`arestaclimb.com`) dois botões claros lado a lado para download de Apple Silicon e Intel.

**Non-Goals:**
- Compilar binário `universal2` único fundido.
- Suporte a arquiteturas obsoletas de 32 bits ou versões de macOS inferiores ao macOS 12 (Monterey).

## Decisions

### 1. Matriz de Build no GitHub Actions (`macos-14` e `macos-13`)
- **Decisão**: Utilizar `strategy.matrix` no workflow `.github/workflows/build_editor_macos.yml` com os runners `macos-14` (Apple Silicon) e `macos-13` (Intel).
- **Rationale**: Permite que o `uv sync --frozen --only-group editor_deploy` baixe diretamente as wheels nativas da plataforma em execução no PyPI, sem emulação lenta ou montagem manual de toolchains cruzadas. Os jobs rodam em paralelo, sem aumentar o tempo total de release.
- **Alternativa descartada**: Compilação cruzada via emulação no mesmo runner (instável, incompatível com PyInstaller e dependências de CFFI/Qt6).

### 2. Convenção e Publicação de Artefatos no Cloudflare R2
- **Decisão**: Nomenclatura previsível dos artefatos:
  - Apple Silicon: `EditorAresta-<versao>-arm64.dmg`, `EditorAresta-arm64-latest.dmg` e `EditorAresta-latest.dmg` (alias).
  - Intel: `EditorAresta-<versao>-intel.dmg` e `EditorAresta-intel-latest.dmg`.
- **Rationale**: Usuários existentes ou links externos que apontavam para `EditorAresta-latest.dmg` continuam recebendo a versão Apple Silicon, enquanto usuários Intel recebem uma URL permanente dedicada (`EditorAresta-intel-latest.dmg`).

### 3. Feed Unificado do Sparkle com `sparkle:hardwareRequirements`
- **Decisão**: O `gerador_feed_sparkle.py` passa a aceitar dados dos dois artefatos (ARM64 e Intel) e gerar dois nós `<item>` dentro do mesmo `appcast.xml`, decorados respectivamente com:
  - `<sparkle:hardwareRequirements>arm64</sparkle:hardwareRequirements>`
  - `<sparkle:hardwareRequirements>x86_64</sparkle:hardwareRequirements>`
- **Rationale**: Funcionalidade nativa do Sparkle 2.x. O cliente in-app no Mac do usuário lê os metadados do processador local e faz download apenas do pacote compatível, evitando que usuários Intel baixem atualizações ARM64 ou vice-versa.
- **Alternativa descartada**: Manter feeds `appcast.xml` separados por arquitetura (exigiria alterar URLs de feed hardcoded nos bundles e complicaria o provisionamento).

### 4. Orquestração de Publicação (Job Agregador de Release)
- **Decisão**: Os jobs da matriz compilam, assinam e notarizam seus respectivos DMGs e disponibilizam os artefatos via `actions/upload-artifact`. Um job subsequente (ou o job que finaliza o feed) assina com a chave Ed25519 do Sparkle ambos os arquivos, gera o `appcast.xml` consolidado e executa `publicar_macos_cli.py`.
- **Rationale**: Garante que o `appcast.xml` contenha as assinaturas criptográficas válidas de ambas as arquiteturas e que a purgação de cache na CDN Cloudflare seja atômica.

### 5. Layout dos Botões na Página do Editor (`arestaclimb.com`)
- **Decisão**: No painel macOS de `editor.html`, colocar dois botões lado a lado em um contêiner flexbox (`flex-wrap: wrap; gap: 14px; justify-content: center;`):
  - Botão 1: **Apple Silicon (M1/M2/M3/M4+)** - destaque primário.
  - Botão 2: **Intel (Macs anteriores a 2020)** - estilo visual integrado ao design system.
- **Rationale**: Atende à solicitação expressa do usuário de botões lado a lado, fornecendo clareza instantânea para quem está em um Mac Intel sem esconder a opção.

## Risks / Trade-offs

- **[Dependência de runner Intel `macos-13` no GitHub]** → O runner `macos-13` é mantido oficialmente pelo GitHub Actions com suporte garantido a x86_64.
- **[Tempo de Notarização Apple em Paralelo]** → A API App Store Connect da Apple processa requisições de notarização concorrentes sem bloqueio de concorrência.
- **[Tamanho do Cache CDN]** → A purgação da Cloudflare já purga até 30 URLs por chamada, absorvendo facilmente os novos arquivos `.dmg`.
