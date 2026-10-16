# Tasks: Distribuição Multi-Arquitetura do Editor macOS (Apple Silicon e Intel)

## 1. Gerador de Feed Sparkle Multi-Arquitetura

- [x] 1.1 Atualizar `editor/release_tools/gerador_feed_sparkle.py` adicionando suporte à inclusão de itens múltiplos decorados com `sparkle:hardwareRequirements` (`arm64` e `x86_64`)
- [x] 1.2 Atualizar e expandir os testes unitários em `editor/release_tools/gerador_feed_sparkle_test.py` cobrindo a geração de feed multi-arquitetura e validar 100% de cobertura

## 2. Parametrização de Arquitetura no Empacotador DMG

- [x] 2.1 Parametrizar `editor/release_tools/empacotar_macos_dmg.py` para aceitar identificador de arquitetura ou sufixo no nome do arquivo `.dmg` gerado (`arm64` e `intel`)
- [x] 2.2 Atualizar a suíte de testes unitários em `editor/release_tools/empacotar_macos_dmg_test.py` e validar 100% de cobertura

## 3. Publicador Cloudflare R2 e CLI

- [x] 3.1 Atualizar `editor/release_tools/publicador_r2_macos.py` e `editor/release_tools/publicar_macos_cli.py` para sincronizar os artefatos de ambas as arquiteturas (`EditorAresta-<versao>-arm64.dmg`, `EditorAresta-arm64-latest.dmg`, `EditorAresta-latest.dmg`, `EditorAresta-<versao>-intel.dmg`, `EditorAresta-intel-latest.dmg`) e purgar suas URLs na CDN Cloudflare
- [x] 3.2 Atualizar os testes unitários em `editor/release_tools/publicador_r2_macos_test.py` e `editor/release_tools/publicar_macos_cli_test.py` mantendo 100% de cobertura

## 4. Pipeline CI/CD GitHub Actions no repositório aresta_db

- [x] 4.1 Atualizar o workflow `.github/workflows/build_editor_macos.yml` implementando matriz com runners nativos `macos-14` (Apple Silicon ARM64) e `macos-13` (Intel x86_64)
- [x] 4.2 Implementar etapa de agregação dos artefatos para geração do `appcast.xml` assinado com chave Ed25519 e execução do CLI de publicação

## 5. Interface de Download no Site arestaclimb.com

- [x] 5.1 Atualizar `editor.html` estruturando dois botões lado a lado no painel macOS: um botão para **Apple Silicon (M1/M2/M3/M4+)** e outro para **Intel (Core i5/i7/i9/Xeon)**
- [x] 5.2 Estilizar em `src/editor.css` o grupo de botões lado a lado com layout flexbox responsivo e suporte a temas claro e escuro
- [x] 5.3 Atualizar os testes em `src/domStructure.test.js` e `src/telemetry.test.js` garantindo que os novos links e eventos sejam validados com 100% de aprovação
