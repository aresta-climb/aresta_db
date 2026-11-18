# Proposal

## Why

Na versão `0.6.2`, todos os usuários do Editor Aresta em Windows (Microsoft Store e Beta MSIX) e macOS (Apple Silicon e Intel DMG) ficaram bloqueados de entrar no aplicativo após a tela de abertura (Issue #100 / Sentry `ARESTA-EDITOR-1E`). Embora `pymupdf` e `ddgs` (`lxml`) tenham sido adicionados ao grupo `editor` do `pyproject.toml`, `obter_modulos_excluidos()` em `editor/build.py` continuou excluindo ambos do bundle PyInstaller, e a falha escapou dos testes de pré-release porque os testes rodavam apenas no `.venv` completo em código-fonte (com o registro MCP desligado no Robô Caótico e sem nenhum smoke test executando o binário congelado gerado).

## What Changes

- **Incorporação integral de dependências do grupo `editor` no PyInstaller e poda cirúrgica de artefatos de build-time**:
  - Remover `pymupdf`, `fitz`, `lxml` e `sqlite3` de `obter_modulos_excluidos()` em `editor/build.py`, garantindo paridade total entre Windows, macOS e Linux Flatpak (inclusive para compilação local do `catalogo.db` em `scripts/gerar_catalogo_sqlite_lib.py`).
  - Garantir coleta íntegra dos binários nativos de `pymupdf` (`mupdfcpp64.dll` / `_mupdf`) e filtrar diretórios de desenvolvimento C/C++ (`mupdf-devel`) em `filtrar_datas_desnecessarios()` e no `cleanup` do manifesto Flatpak (`com.arestaclimb.Editor.yaml`).
  - Remover o `hiddenimport` órfão `scripts.finalizar_mapas` de `editor/EditorAresta.spec`.
- **BREAKING (interno): Registro obrigatório do `ServidorMCP` no ciclo de vida do Editor**:
  - Remover o parâmetro legado `iniciar_mcp` de `ControladorAplicativo`, `JanelaPrincipal` e `MotorRoboCaoticoQt`, substituindo-o por `iniciar_rede_mcp: bool = True` para que o `ServidorMCP` e 100% de suas ferramentas (`conhecimento`, `ciclo_vida`, `comandos`, `visao` e `betas`) sejam sempre instanciados e registrados (mesmo em testes rápidos em memória e no Robô Caótico).
- **Resiliência contra processos zumbis em falhas fatais de transição de janelas**:
  - Proteger `ControladorAplicativo.executar_selecao()` e `mostrar_janela_principal()` para que qualquer exceção não tratada após o fechamento da `TelaDeAbertura` seja reportada à telemetria, exibida de forma visível ao usuário (`mostrar_erro`) e encerre o processo e o servidor de instância única de forma limpa.
- **Testes reais de contrato de empacotamento sem mocks internos**:
  - Refatorar `editor/build_test.py` eliminando mocks internos (`patch("PyInstaller.__main__.run")`, `MagicMock` de `Path.exists`/`PIL`) e testes *change-detector*, introduzindo validação automática de que nenhum pacote exportado pelo grupo `editor` (`uv.lock`) ou importado por `editor/`, `coleta_de_betas/` e `migracoes/` consta em `obter_modulos_excluidos()`, e de que todos os `hiddenimports` de `EditorAresta.spec` são importáveis.
- **Gate obrigatório de Smoke Test Pós-Build offline nos binários finais multiplataforma**:
  - Criar a biblioteca e CLI `editor/release_tools/smoke_test_pacote.py` (com suporte no binário via `--smoke-test`) que levanta em loopback (`127.0.0.1`) um servidor HTTP local compatível com Supabase Auth OTP e um repositório Git real em disco, executa o binário empacotado real (`QT_QPA_PLATFORM=offscreen`, sem uso de rede externa), realiza login OTP na `TelaDeAbertura`, clona via `pygit2`, conecta ao `ServidorMCP` HTTP real na `TelaDeCarregamento`, cria/abre um croqui na `JanelaPrincipal`, particiona um PDF real (`pymupdf` + WebP), valida `ddgs`/`lxml` e compila/salva o croqui antes de encerrar com código `0`.
  - Integrar o smoke test pós-build como barreira obrigatória antes da publicação em `build_editor_windows.yml` (Beta e Produção Store), `build_editor_macos.yml` (Apple Silicon nativo e Intel `x86_64` via Rosetta 2, além de verificação da arquitetura Mach-O) e `build_editor_linux.yml` (Flatpak), mantendo o cut prévio de versão em `prepare_release` no `release-editor.yml`.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capacidade isolada; os comportamentos estendem capacidades existentes do Editor e CI/CD. -->

### Modified Capabilities
- `otimizacao-build-editor`: Atualiza os requisitos de isolamento de dependências para incorporar `pymupdf` e `lxml` (removendo apenas headers `mupdf-devel`), exige validação automatizada de consistência entre `uv.lock`/imports e `obter_modulos_excluidos()`/`EditorAresta.spec`, e proíbe mocks internos nos testes de build.
- `editor-inicializacao`: Torna obrigatório o registro do `ServidorMCP` e de todas as suas ferramentas na inicialização (`iniciar_rede_mcp`), impede processos zumbis silenciosos em falhas durante transições de janelas e adiciona suporte ao modo de autoverificação ponta a ponta (`--smoke-test`).
- `editor-workflow-release`: Preserva o cut prévio da versão no job `prepare_release` e exige a execução bem-sucedida do smoke test pós-build offline sobre o pacote compilado em Windows, macOS (ARM64 e Intel sob Rosetta 2) e Linux Flatpak antes de qualquer etapa de publicação externa (Cloudflare R2, Sparkle e Microsoft Store).

## Impact

- **Empacotamento e Build**: `editor/build.py`, `editor/build_test.py`, `editor/EditorAresta.spec`, `editor/flatpak/com.arestaclimb.Editor.yaml`.
- **Ciclo de Vida e Caos do Editor**: `editor/main.py`, `editor/main_test.py`, `editor/legacy_views/area_principal.py`, `editor/legacy_views/area_principal_test.py`, `editor/caos/motor_robo_caotico.py`.
- **Ferramental de Release e CI/CD**: `editor/release_tools/smoke_test_pacote.py`, `editor/release_tools/smoke_test_pacote_test.py`, `.github/workflows/build_editor_windows.yml`, `.github/workflows/build_editor_macos.yml`, `.github/workflows/build_editor_linux.yml`, `tests/workflow_release_editor_test.py`.
