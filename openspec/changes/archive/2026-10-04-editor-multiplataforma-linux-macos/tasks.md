## 1. Teste de Integração e Abstração de Plataforma (TDD)

- [x] 1.1 Criar o teste de integração de fronteiras de plataforma (`tests/fronteiras_plataforma_test.py`) via AST e verificar que ele falha antes da criação da estrutura (ciclo Red)
- [x] 1.2 Criar os testes unitários da biblioteca `editor/plataforma/` (`editor/plataforma/contrato_test.py` e `editor/plataforma/__init___test.py`) e implementar a fachada agnóstica mínima em português brasileiro para fazê-los passar com 100% de cobertura (ciclo Green)
- [x] 1.3 Migrar as rotinas de Windows para `editor/plataforma/windows/` (`integracao.py` e `servico_loja.py`), cobrindo `configurar_identidade_processo_windows`, `configurar_presenca_barra_de_tarefas`, `trazer_janela_para_frente` e `ServicoLoja`, criando `integracao_test.py` e `servico_loja_test.py` acompanhados no mesmo diretório com 100% de cobertura
- [x] 1.4 Criar `editor/plataforma/linux/integracao_test.py` e implementar `editor/plataforma/linux/integracao.py` com resolução de diretórios XDG, ativação de janelas via Qt e 100% de cobertura
- [x] 1.5 Criar `editor/plataforma/macos/integracao_test.py` e implementar `editor/plataforma/macos/integracao.py` com resolução de diretórios de Application Support, ativação de janelas e 100% de cobertura
- [x] 1.6 Refatorar `editor/main.py` e `editor/core/storage.py` para consumir exclusivamente `editor.plataforma`, preservando rigorosamente o arranque rápido (< 1s) e o padrão de importações sob demanda (`__getattr__`), garantindo que `tests/fronteiras_plataforma_test.py` e `editor/main_test.py` passem integralmente

## 2. Ajustes de Empacotamento Cross-Platform no PyInstaller (TDD)

- [x] 2.1 Atualizar `editor/build_test.py` com testes para filtros de bibliotecas dinâmicas Unix (`.so`, `.dylib`) na estrutura `onedir` gerada por `COLLECT` e estender `editor/build.py` e `editor/EditorAresta.spec` para fazê-los passar com 100% de cobertura
- [x] 2.2 Adicionar teste unitário em `editor/build_test.py` e `editor/core/configuracao_canal_test.py` para geração de ícone `.icns` a partir de `recursos/logo_app.png` e integração com `obter_caminho_icone_aplicacao()` no macOS, implementando a rotina correspondente

## 3. Empacotamento e Distribuição macOS (TDD)

- [x] 3.1 Criar `editor/release_tools/gerador_feed_sparkle_test.py` e implementar `editor/release_tools/gerador_feed_sparkle.py` para geração do XML assinado com Ed25519 com 100% de cobertura de testes unitários
- [x] 3.2 Criar `editor/release_tools/empacotar_macos_dmg_test.py` e implementar `editor/release_tools/empacotar_macos_dmg.py` utilizando o diretório `dist/EditorAresta` gerado pelo PyInstaller para montagem do bundle `EditorAresta.app`, assinatura e geração do DMG com validação em modo dry-run e 100% de cobertura

## 4. Empacotamento e Distribuição Linux (TDD)

- [x] 4.1 Criar teste de validação de metadados em `tests/manifesto_flatpak_test.py` verificando a conformidade estrutural do manifesto e arquivos AppStream
- [x] 4.2 Criar o manifesto Flatpak `dist/flatpak/com.arestaclimb.Editor.yaml`, metadados AppStream `dist/flatpak/com.arestaclimb.Editor.metainfo.xml` e arquivo de desktop `dist/flatpak/com.arestaclimb.Editor.desktop`, fazendo o teste passar

## 5. Pipeline CI/CD Multiplataforma

- [x] 5.1 Atualizar `.github/workflows/release-editor.yml` adicionando o job de compilação, assinatura Developer ID, notarização Apple e upload para o Cloudflare R2 em runner `macos-14` (ARM64)
- [x] 5.2 Adicionar etapa no pipeline de release para sincronização com o repositório do Flathub
- [x] 5.3 Atualizar os testes do workflow (`tests/workflow_release_editor_test.py`) garantindo cobertura de 100% dos novos jobs

## 6. Verificação de Cobertura e Integridade (100% Coverage)

- [x] 6.1 Executar a suíte completa com `uv run pytest --cov=editor` e certificar 100% de cobertura de testes unitários sem nenhuma regressão, validando os 7 Princípios de Engenharia Aresta
