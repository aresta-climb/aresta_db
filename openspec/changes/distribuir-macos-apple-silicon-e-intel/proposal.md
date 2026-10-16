# Proposal: Distribuição do Editor Aresta para macOS em Apple Silicon e Intel

## Why

Atualmente, o pipeline de release do Editor Aresta para macOS compila e distribui binários exclusivamente para a arquitetura Apple Silicon (ARM64, processadores M1/M2/M3/M4+). Quando usuários de computadores Mac com processadores Intel (x86_64) tentam abrir o aplicativo, o Finder impede a execução exibindo o ícone de bloqueio e a mensagem *"You can't open the application 'EditorAresta' because this application is not supported on this Mac"*. Como o macOS não possui emulação reversa (o Rosetta 2 traduz apenas de Intel para Apple Silicon, mas não de ARM64 para Intel), usuários de computadores Mac com processadores Intel ficam impossibilitados de executar o editor.

Para atender plenamente a comunidade de escaladores e autores de croquis que utilizam computadores Apple com processadores Intel, precisamos compilar, assinar, notarizar e disponibilizar instaladores independentes para ambas as arquiteturas, além de permitir auto-atualizações in-app transparentes e botões claros de download.

## What Changes

- **Matriz de Build no GitHub Actions para macOS**:
  - Configuração de matriz no workflow `.github/workflows/build_editor_macos.yml` utilizando runners nativos da GitHub: `macos-14` para Apple Silicon (`arm64`) e `macos-13` para Intel (`x86_64`).
- **Geração de Imagens de Disco (DMG) Notarizadas por Arquitetura**:
  - Geração e assinatura com Developer ID e notarização Apple independente para cada arquitetura:
    - Apple Silicon: `EditorAresta-<versao>-arm64.dmg` (com alias de compatibilidade `EditorAresta-latest.dmg` e `EditorAresta-arm64-latest.dmg`).
    - Intel: `EditorAresta-<versao>-intel.dmg` (e `EditorAresta-intel-latest.dmg`).
- **Feed Multi-Arquitetura do Sparkle Framework (`appcast.xml`)**:
  - Evolução do `gerador_feed_sparkle.py` para suportar itens simultâneos diferenciados pela diretiva nativa `<sparkle:hardwareRequirements>arm64</sparkle:hardwareRequirements>` e `<sparkle:hardwareRequirements>x86_64</sparkle:hardwareRequirements>`, garantindo que cada máquina baixe a atualização correta sem intervenção manual.
- **Publicador Cloudflare R2 e CLI de Publicação**:
  - Atualização de `publicador_r2_macos.py` e `publicar_macos_cli.py` para sincronizar os artefatos de ambas as arquiteturas e purgar os respectivos endpoints na CDN Cloudflare.
- **Interface de Download no Site (`arestaclimb.com`)**:
  - Na aba macOS do `editor.html`, disponibilização de botões lado a lado para download direto de **Apple Silicon (M1/M2/M3/M4+)** e **Intel (Core i5/i7/i9/Xeon)**.

## Capabilities

### Modified Capabilities
- `editor-distribuicao-macos`: Expandir os requisitos de empacotamento, distribuição, notarização Apple e feed Sparkle para contemplar explicitamente as duas arquiteturas de processador suportadas (Apple Silicon `arm64` e Intel `x86_64`).

## Impact

- **Código de Produção**:
  - `editor/release_tools/empacotar_macos_dmg.py`: identificação/parametrização do sufixo de arquitetura no nome do DMG gerado.
  - `editor/release_tools/gerador_feed_sparkle.py`: suporte a itens múltiplos com `sparkle:hardwareRequirements`.
  - `editor/release_tools/publicador_r2_macos.py` e `publicar_macos_cli.py`: publicação dos artefatos versionados e latest de ARM64 e Intel.
  - `.github/workflows/build_editor_macos.yml`: matriz de build com `macos-14` e `macos-13`.
- **Testes Unitários**:
  - `editor/release_tools/empacotar_macos_dmg_test.py`, `gerador_feed_sparkle_test.py`, `publicador_r2_macos_test.py` e `publicar_macos_cli_test.py` mantendo 100% de cobertura.
- **Site Institucional (`arestaclimb.com`)**:
  - `editor.html`, `src/editor.css` e testes em `src/domStructure.test.js` e `src/editor.test.js`.
