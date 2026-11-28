# Proposal

## Why

O banner amarelo da seção `1. Betas Não Scorados` no `PainelCuradoria` passou a exibir o texto bruto completo do prompt MCP na interface, poluindo a leitura humana quando deveria apenas orientar em dois passos curtos e deixar o prompt técnico exclusivamente no botão **"📋 Copiar Prompt MCP"**. Além disso, ao executar o editor via Python desempacotado (`uv run editor/main.py ...`) no Windows 11, o ícone do Aresta deixou de ser aplicado de forma confiável na janela/barra de tarefas (devido à chamada global de `AppUserModelID` em tempo de `import`, ausência de metadados visuais registrados para o `AppUserModelID` desempacotado e mutação de `WindowFlags`/estilos Win32 após `setWindowIcon`) e a abertura da `JanelaPrincipal` após o fechamento da tela inicial apresenta vários segundos sem janela visível porque *imports* pesados, leitura/hidratação síncrona do croqui, instanciação ansiosa de abas secundárias (`Dados` e `Imagens`) e espera bloqueante do `ServidorMCP` ocorrem na thread de UI.

## What Changes

- **Simplificação visual do banner MCP em `PainelCuradoria`**: `gerar_instrucoes_banner_mcp_avaliacao` exibirá apenas 2 passos enxutos e legíveis (conectar ao servidor MCP `editor-aresta` e clicar em **"📋 Copiar Prompt MCP"** para colar no agente), mantendo o prompt técnico completo e contextualizado (`id_croqui`, `aresta_ler_skill`, `editor-aresta`) exclusivamente na ação de cópia para a área de transferência.
- **Aplicação determinística do ícone da aplicação e janela no Windows 11**:
  - Remoção da chamada `configurar_identidade_processo` do escopo de `import` de `editor/main.py`, executando-a exclusivamente no arranque gráfico real antes de instanciar `QApplication` (nunca em `--headless` nem ao importar o módulo em suítes de teste).
  - Registro determinístico de `DisplayName` e `IconUri` em `HKCU\Software\Classes\AppUserModelId\<app_user_model_id>` para processos Windows fora de pacote MSIX, tipagem explícita de `SetCurrentProcessExplicitAppUserModelID` e reforço nativo de `WM_SETICON` (`ICON_SMALL` e `ICON_BIG`) + `SWP_FRAMECHANGED` ao configurar janelas top-level.
  - Ordenação consistente de `setWindowFlags` antes de `setWindowIcon` em `TelaDeCarregamento` e reaplicação do ícone após `configurar_presenca_barra_de_tarefas` em `TelaDeAbertura` e `DialogoRecuperacaoSessao`.
- **Carregamento pesado do croqui em background (`Library-First`) e abertura imediata da `JanelaPrincipal`**:
  - Extração de uma biblioteca dedicada (`editor/core/carregador_croqui.py`) que executa fora da UI thread a migração, leitura de `croqui.yaml`, hidratação dos arquivos externos (`.md`/`curadoria_betas.yaml`) na árvore Protobuf pura, avaliação inicial de `ResultadoNotaQualidade` e obtenção de `commit_base_sha` (`git rev-parse HEAD`), produzindo um `PacoteCroquiCarregado` imutável.
  - Execução integrada dessa carga pesada (junto ao pré-aquecimento dos *imports* pesados da `JanelaPrincipal`) dentro da `TarefaInicializacao` (`QThread`) quando o croqui já é informado na linha de comando, e via `TarefaCarregamentoCroqui` (`QThread`) ao abrir um croqui pela `TelaDeCarregamento`, eliminando o intervalo sem janelas visíveis na transição e abrindo `DialogoRecuperacaoSessao` somente após `janela_principal.show()`.
  - Conversão de `PaginaDados` (`WidgetEditorDados`) e `PaginaImagens` (`WidgetEditorImagens`) para carregamento sob demanda (*lazy loading*), reutilização da `ResultadoNotaQualidade` pré-calculada em `WidgetPainelQualidade`, remoção do registro duplicado de ferramentas MCP e partida não-bloqueante da thread Uvicorn na abertura da `JanelaPrincipal`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `curation-panel`: O banner da seção `1. Betas Não Scorados` passa a exibir apenas instruções humanas resumidas em 2 passos, mantendo o prompt MCP técnico completo exclusivamente na cópia via botão **"📋 Copiar Prompt MCP"**.
- `editor-inicializacao`: Identidade de processo (`AppUserModelID`) restrita ao arranque gráfico real com metadados de ícone registrados no Shell do Windows, reforço Win32 de ícone na barra de tarefas/título e pré-aquecimento/pré-carregamento em background durante `TarefaInicializacao` e `TelaDeCarregamento` sem lacuna visual entre janelas.
- `editor-area-principal`: Hidratação instantânea da `JanelaPrincipal` a partir de `PacoteCroquiCarregado`, carregamento sob demanda (*lazy loading*) estendido às abas **Dados** e **Imagens**, exibição de `DialogoRecuperacaoSessao` apenas com a janela principal já visível e inicialização não-bloqueante do `ServidorMCP`.

## Impact

- `coleta_de_betas/curadoria/painel_curadoria.py` e `coleta_de_betas/curadoria/painel_curadoria_test.py`
- `editor/plataforma/contrato.py`, `editor/plataforma/__init__.py`, `editor/plataforma/adaptador_plataforma_fake.py`, `editor/plataforma/windows/integracao.py`, `editor/plataforma/windows/api_win32_fake.py` e respectivos `*_test.py`
- `editor/core/carregador_croqui.py` e `editor/core/carregador_croqui_test.py`
- `editor/core/worker.py`, `editor/main.py`, `editor/views/tela_de_abertura.py`, `editor/views/dialogo_recuperacao_sessao.py`, `editor/views/widget_painel_qualidade.py`, `editor/legacy_views/tela_de_carregamento.py`, `editor/legacy_views/area_principal.py` e respectivos `*_test.py`
