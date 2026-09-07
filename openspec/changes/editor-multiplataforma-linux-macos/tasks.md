## 1. Teste de Integração e Abstração de Plataforma (TDD)

- [ ] 1.1 Criar o teste de integração de fronteiras de plataforma (`tests/fronteiras_plataforma_test.py`) via AST e verificar que ele falha antes da criação da estrutura (ciclo Red)
- [ ] 1.2 Criar os testes unitários da biblioteca `editor/plataforma/` (`editor/plataforma/contrato_test.py` e `editor/plataforma/__init___test.py`) e implementar a fachada agnóstica mínima em português brasileiro para fazê-los passar com 100% de cobertura (ciclo Green)
- [ ] 1.3 Migrar as rotinas de Windows para `editor/plataforma/windows/` (`integracao.py` e `servico_loja.py`), criando `integracao_test.py` e `servico_loja_test.py` acompanhados no mesmo diretório com 100% de cobertura
- [ ] 1.4 Criar `editor/plataforma/linux/integracao_test.py` e implementar `editor/plataforma/linux/integracao.py` com resolução de diretórios XDG e 100% de cobertura
- [ ] 1.5 Criar `editor/plataforma/macos/integracao_test.py` e implementar `editor/plataforma/macos/integracao.py` com resolução de diretórios de Application Support e 100% de cobertura
- [ ] 1.6 Refatorar `editor/main.py` e `editor/core/storage.py` para consumir exclusivamente `editor.plataforma`, garantindo que `tests/fronteiras_plataforma_test.py` passe integralmente

## 2. Ajustes de Empacotamento Cross-Platform no PyInstaller (TDD)

- [ ] 2.1 Atualizar `editor/build_test.py` com testes para filtros de bibliotecas dinâmicas Unix (`.so`, `.dylib`) e estender `editor/build.py` e `editor/EditorAresta.spec` para fazê-los passar com 100% de cobertura
- [ ] 2.2 Adicionar teste unitário em `editor/build_test.py` para geração de ícone `.icns` a partir de `recursos/logo_app.png` e implementar a rotina correspondente em `editor/build.py`

## 3. Empacotamento e Distribuição macOS (TDD)

- [ ] 3.1 Criar `editor/release_tools/gerador_feed_sparkle_test.py` e implementar `editor/release_tools/gerador_feed_sparkle.py` para geração do XML assinado com Ed25519 com 100% de cobertura de testes unitários
- [ ] 3.2 Criar `editor/release_tools/empacotar_macos_dmg_test.py` e implementar `editor/release_tools/empacotar_macos_dmg.py` com validação de modo dry-run e 100% de cobertura de testes unitários

## 4. Empacotamento e Distribuição Linux (TDD)

- [ ] 4.1 Criar teste de validação de metadados em `tests/manifesto_flatpak_test.py` verificando a conformidade estrutural do manifesto e arquivos AppStream
- [ ] 4.2 Criar o manifesto Flatpak `dist/flatpak/com.arestaclimb.Editor.yaml`, metadados AppStream `dist/flatpak/com.arestaclimb.Editor.metainfo.xml` e arquivo de desktop `dist/flatpak/com.arestaclimb.Editor.desktop`, fazendo o teste passar

## 5. Pipeline CI/CD Multiplataforma

- [ ] 5.1 Atualizar `.github/workflows/release-editor.yml` adicionando o job de compilação, assinatura Developer ID, notarização Apple e upload para o Cloudflare R2 em runner `macos-14` (ARM64)
- [ ] 5.2 Adicionar etapa no pipeline de release para sincronização com o repositório do Flathub
- [ ] 5.3 Atualizar os testes do workflow (`tests/workflow_release_editor_test.py`) garantindo cobertura de 100% dos novos jobs

## 6. Verificação de Cobertura e Integridade (100% Coverage)

- [ ] 6.1 Executar a suíte completa com `uv run pytest --cov=editor` e certificar 100% de cobertura de testes unitários sem nenhuma regressão, validando os 7 Princípios de Engenharia Aresta
