## Context

Veja `proposal.md - Why`. Atualmente, a integração com o sistema operacional no Editor Aresta está dispersa em arquivos no diretório `editor/core/` (`integracao_windows.py`, `servico_loja.py`) e acoplada a chamadas do Windows no `main.py`. Além disso, o pipeline de release em `.github/workflows/release-editor.yml` roda unicamente em runners `windows-latest`.

## Alinhamento com os Princípios de Engenharia Aresta

Esta proposta e design seguem estritamente as diretrizes inegociáveis de `AGENTS.md` e da skill `principios_desenvolvimento`:

1. **I. Tudo em Português:** Todo o novo pacote é batizado como `editor/plataforma/`, e todos os arquivos, funções, métodos, classes, variáveis e comentários são redigidos em português brasileiro (ex: `editor/plataforma/contrato.py`, `editor/release_tools/gerador_feed_sparkle.py`, `editor/release_tools/empacotar_macos_dmg.py`, `tests/fronteiras_plataforma_test.py`).
2. **II. Library-First (Biblioteca em Primeiro Lugar):** O módulo `editor/plataforma/` é concebido como uma biblioteca independente e autossuficiente com interface clara e documentada, que pode ser testada e consumida sem acoplamento a visões da UI.
3. **III. 100% de Unit Test Coverage:** Todo arquivo de código de produção introduzido terá 100% de cobertura de testes unitários garantida, sem exceções.
4. **IV. Imperativo do Teste em Primeiro Lugar (TDD):** Segue estritamente o ciclo Red-Green-Refactor. Todo arquivo `.py` DEVE ter um `_test.py` acompanhando no mesmo diretório. Os testes devem ser escritos e falhar antes da implementação do código de produção correspondente.
5. **V. Testes de Integração em Primeiro Lugar:** O teste de fronteiras e isolamento (`tests/fronteiras_plataforma_test.py`) é estabelecido e executado antes da implementação aprofundada dos adaptadores específicos, garantindo a integridade dos contratos e a ausência de vazamento de APIs nativas.
6. **VI. Simplicidade e Anti-Abstração:** Sem hierarquias complexas de classes, fábricas abstratas dinâmicas ou metaprogramação. O despachador em `editor/plataforma/__init__.py` consulta diretamente `sys.platform` de forma declarativa e simples para selecionar as funções do SO correspondente.
7. **VII. Edições de Estado via Comandos do Histórico:** As rotinas de empacotamento, checagem de versão e plataforma não realizam mutações no estado do croqui; qualquer ação disparada na UI preserva o padrão de comandos do histórico existente.

## Goals / Non-Goals

**Goals:**
- Centralizar integrações de sistema operacional em uma biblioteca limpa sob `editor/plataforma/`.
- Garantir via teste de linting baseado em AST que nenhum módulo externo acesse APIs nativas de plataforma.
- Criar o manifesto Flatpak e arquivos AppStream para publicação no Flathub.
- Criar o pipeline de empacotamento, assinatura Developer ID, notarização Apple e geração de feed Sparkle (`appcast.xml`) para macOS ARM64 hospedado no Cloudflare R2.
- Unificar a cadência de lançamentos: macOS e Linux publicam na track de produção com deploys automatizados e rápidos.

**Non-Goals:**
- Suporte a arquitetura Intel (x86_64) no macOS (escopo focado estritamente em Apple Silicon ARM64).
- Criação de tracks Beta para Linux ou macOS (o conceito de Beta permanece restrito ao Windows para contornar a certificação da Microsoft Store).
- Publicação na Mac App Store (evitada devido a restrições severas de sandbox para interpretadores Python, subprocessos e operações Git).

## Decisions

### Decisão 1: Biblioteca `editor/plataforma/` com Fachada Agnóstica e Teste AST
- **Abordagem:** Criar a biblioteca `editor/plataforma/` contendo `__init__.py` (fachada pública declarativa), `contrato.py` (protocolo simples), `windows/`, `linux/` e `macos/`. O código do editor consome apenas funções agnósticas (ex: `configurar_ambiente_plataforma()`, `verificar_atualizacoes_plataforma()`).
- **Alternativas consideradas:**
  - Manter verificações `if sys.platform == "win32"` espalhadas no código: Rejeitado por degradar a manutenibilidade e violar o princípio *Library-First*.
- **Garantia Arquitetural:** Teste de integração (`tests/fronteiras_plataforma_test.py`) utilizando o módulo `ast` do Python que varre `editor/` e garante que nenhuma importação de `winrt`, `ctypes.windll`, `objc` ou módulos de plataforma ocorra fora de `editor/plataforma/`.

### Decisão 2: Linux via Flatpak / Flathub (Track Única de Produção)
- **Abordagem:** Criar o manifesto `com.arestaclimb.Editor.yaml` para compilação na infraestrutura do Flathub.
- **Alternativas consideradas:**
  - Repositório OSTree próprio no Cloudflare R2: Rejeitado pela complexidade desnecessária de sincronização de deltas e manutenção de repositório manual.
  - AppImage: Considerado, mas o Flatpak oferece integração superior com lojas de aplicativos do ecossistema Linux (GNOME Software, KDE Discover).

### Decisão 3: macOS via DMG Notarizado ARM64 e Sparkle Framework no Cloudflare R2
- **Abordagem:** Runner `macos-14` do GitHub Actions compila com PyInstaller para ARM64, assina com certificado *Developer ID Application*, submete ao `xcrun notarytool`, gera o `.dmg` e atualiza o feed `appcast.xml` no Cloudflare R2. O aplicativo integra o Sparkle Framework para auto-update in-app nativo.
- **Alternativas consideradas:**
  - Mac App Store: Rejeitada devido a exigências restritivas de App Sandbox que conflitam com Git (`pygit2`), servidores locais e PyInstaller.
  - Verificação manual in-app de JSON: O Sparkle oferece experiência superior ao usuário (download em segundo plano, validação criptográfica Ed25519 e substituição atômica do `.app`).

### Decisão 4: Eliminação de Track Beta no Linux e macOS
- **Abordagem:** No Linux e macOS, todo lançamento é oficial e direto. Apenas o Windows mantém o canal Beta no Cloudflare R2.
- **Rationale:** A limitação de tempo de revisão existe apenas na Microsoft Store. Eliminar tracks secundárias em Linux e macOS poupa esforço de infraestrutura e mantém o repositório simples (*Princípio VI: Simplicidade e Anti-Abstração*).

## Risks / Trade-offs

- [Falta de máquina Mac física para testes locais] → Mitigation: O workflow do GitHub Actions em runners `macos-14` (gratuitos para repositórios públicos) fornece ambiente limpo Apple Silicon para testes automatizados e compilação.
- [Dependência do Sparkle em Python] → Mitigation: Utilizar ferramentas CLI do Sparkle no pipeline de build para assinar com Ed25519 e gerar o XML, mantendo a camada Python no app apenas consumindo ou disparando a verificação de forma enxuta.
- [Acesso a arquivos no sandbox do Flatpak] → Mitigation: Configurar permissões de sistema de arquivos adequadas no manifesto e certificar o uso de XDG Desktop Portals via PySide6.
