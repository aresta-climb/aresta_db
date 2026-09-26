## Why

Atualmente, o Editor Aresta leva entre 20 e 30 segundos para exibir sua primeira janela visual (a tela de splash/login ou a janela principal em modo local). Essa lentidão severa afeta tanto os usuários finais do pacote instalado quanto os desenvolvedores executando via terminal (`uv run editor/main.py`), degradando a percepção de performance e a experiência de uso.

A investigação revelou quatro gargalos concorrentes: o empacotamento do executável em modo `onefile` com UPX forçando extração de 118MB em `%TEMP%` sob varredura síncrona do antivírus; a inicialização bloqueante do Sentry na primeira linha do Python inspecionando 177 pacotes virtuais com integrações web/IA irrelevantes para desktop; imports antecipados de todo o grafo de dependências no topo de `main.py`; e a instanciação síncrona antecipada de todas as abas pesadas (como o editor de mapas e o painel de curadoria de betas) antes de exibir a janela principal.

## What Changes

- **Empacotamento `onedir` para MSIX**: Alteração do `EditorAresta.spec` e `editor/build.py` para gerar uma pasta de distribuição (`onedir` com `COLLECT`) em vez de um único arquivo autoextrator (`onefile`), desativando a compressão UPX em tempo de execução. O workflow de release empacota o diretório completo no contêiner MSIX.
- **Otimização da Telemetria Sentry**: Configuração do `sentry_sdk.init` com `auto_enabling_integrations=False` em `editor/core/telemetria.py`, eliminando a varredura e importação de bibliotecas web/IA do ambiente virtual, além de garantir que a inicialização da telemetria não bloqueie a renderização do primeiro frame da interface.
- **Arranque Rápido com Imports sob Demanda (Lazy Imports)**: Reorganização de `editor/main.py` para remover imports pesados do nível do módulo (`TelaDeCarregamento`, `TarefaInicializacao`, `ClienteAuthSupabase`). A criação do `QApplication` e a exibição da janela ocorrem imediatamente, importando apenas os módulos estritamente necessários para o modo em execução (Modo Local vs Modo Padrão).
- **Carregamento Preguiçoso de Abas na Janela Principal**: Alteração em `editor/legacy_views/area_principal.py` para instanciar o `WidgetEditorMapas` somente quando o usuário navegar para a aba "Mapas", e não instanciar o `PainelCuradoria` enquanto a aba "Betas" estiver oculta.

## Capabilities

### New Capabilities

### Modified Capabilities
- `editor-inicializacao`: Otimização do ciclo de arranque da aplicação com imports sob demanda e exibição imediata da janela gráfica antes de carregar módulos auxiliares.
- `otimizacao-build-editor`: Transição do empacotamento do executável de `onefile` para `onedir` para integração direta com o contêiner MSIX sem extração temporária.
- `editor-telemetria-crash`: Inicialização enxuta e não bloqueante do SDK Sentry, desativando integrações automáticas dispensáveis para desktop.
- `editor-area-principal`: Instanciação sob demanda (lazy loading) das abas da Janela Principal, reduzindo o tempo de carregamento síncrono inicial de croquis.

## Impact

- **Código Afetado**:
  - `editor/EditorAresta.spec` e `editor/build.py` (troca de `onefile` para `onedir` via `COLLECT`).
  - `.github/workflows/release-editor.yml` (cópia da pasta de build para o staging do MSIX).
  - `editor/core/telemetria.py` (desativação de auto-enabling integrations no Sentry).
  - `editor/main.py` (reordenação do ciclo de boot e imports locais sob demanda).
  - `editor/legacy_views/area_principal.py` (lazy loading de páginas do stacked widget).
- **Desempenho**: Redução do tempo de aparecimento da primeira janela de ~20-30s para < 1s (tanto no executável instalado quanto em desenvolvimento local via `uv run`).
- **Compatibilidade**: Total compatibilidade mantida com pacotes MSIX existentes da Microsoft Store e canal Beta, sem quebra de APIs ou contratos de dados.
