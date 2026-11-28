# Tasks

## 1. Simplificação do Banner MCP em `PainelCuradoria`

- [x] 1.1 Atualizar `coleta_de_betas/curadoria/painel_curadoria_test.py` e `coleta_de_betas/curadoria/painel_curadoria.py` via TDD para que `gerar_instrucoes_banner_mcp_avaliacao` retorne apenas instruções curtas em 2 passos legíveis (sem embutir o prompt MCP bruto), mantendo o prompt contextualizado completo exclusivamente em `gerar_prompt_mcp_avaliacao_betas` / `_copiar_prompt_mcp`, e verificar aprovação com `uv run pytest coleta_de_betas/curadoria/painel_curadoria_test.py`.

## 2. Identidade de Processo e Ícone Determinístico no Windows 11

- [x] 2.1 Criar a biblioteca `test-only` `editor/plataforma/windows/api_win32_fake.py` com seu teste espelhado `editor/plataforma/windows/api_win32_fake_test.py`, estender `AdaptadorPlataforma` (`contrato.py`, `__init__.py`, `adaptador_plataforma_fake.py`, `linux/integracao.py`, `macos/integracao.py` e `windows/integracao.py`) com registro de `AppUserModelId` (`DisplayName` e `IconUri` em `HKCU\Software\Classes\AppUserModelId`) e `aplicar_icone_janela_nativa` (`WM_SETICON` + `SWP_FRAMECHANGED`), refatorando `integracao_test.py` sem `MagicMock` e verificando 100% de cobertura em `editor/plataforma/`.
- [x] 2.2 Remover `configurar_identidade_processo` do escopo de `import` de `editor/main.py` (chamando-a apenas no arranque gráfico real antes de `QApplication`), corrigir a ordem de `setWindowFlags` vs `setWindowIcon` e reforço nativo de ícone em `TelaDeAbertura`, `TelaDeCarregamento`, `JanelaPrincipal` e `DialogoRecuperacaoSessao`, verificando aprovação nos testes correspondentes.

## 3. Carregamento Pesado em Background e Abas Sob Demanda (*Lazy Loading*)

- [x] 3.1 Criar `editor/core/carregador_croqui.py` e `editor/core/carregador_croqui_test.py` via TDD para hidratar fora da UI thread a árvore Protobuf completa (`croqui.yaml`, `.md`, `curadoria_betas.yaml`, `commit_base_sha` e `ResultadoNotaQualidade` inicial) e integrar `CroquiModel.criar_de_pacote_carregado`, verificando 100% de cobertura de `carregador_croqui.py`.
- [x] 3.2 Integrar o pré-aquecimento de módulos e o carregamento assíncrono do pacote em `TarefaInicializacao` (`editor/core/worker.py`) e `TarefaCarregamentoCroqui` / `TelaDeCarregamento`, além de tornar `PaginaDados` e `PaginaImagens` sob demanda (*lazy*), reutilizar `ResultadoNotaQualidade` inicial em `WidgetPainelQualidade`, exibir `DialogoRecuperacaoSessao` somente após `janela_principal.show()` e remover o bloqueio de espera/registro duplicado do `ServidorMCP` na abertura de `JanelaPrincipal`, verificando aprovação nos testes de `worker`, `main`, `tela_de_carregamento` e `area_principal`.

## 4. Verificação Integrada de Qualidade e Cobertura

- [x] 4.1 Executar `ruff check`, `mypy` e `pytest --cov` sobre todos os módulos alterados e o teste de fronteiras de plataforma, confirmando 100% de cobertura nos novos módulos, ausência de regressões e conformidade integral com `AGENTS.md`.

## Workflow follow-up

- Sincronizar as delta specs com `openspec/specs/`, validar com `openspec validate --specs` e arquivar a change em `openspec/changes/archive/`.
- Realizar commit com `Signed-off-by` (apenas arquivos escopados desta mudança) e enviar `git push`.
