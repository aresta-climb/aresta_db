## Context

O Editor Aresta atualmente sofre com um tempo excessivo de inicialização (20 a 30 segundos) antes da renderização do primeiro frame visual (splash screen ou janela principal em modo local).
A análise diagnóstica identificou que esse tempo decorre do efeito acumulado de quatro fatores:
1. O empacotamento PyInstaller em modo `onefile` com UPX, que obriga o desempacotamento de 118MB em `%TEMP%` a cada inicialização, submetendo cada DLL à verificação síncrona do Windows Defender;
2. A inicialização padrão do SDK Sentry (`auto_enabling_integrations=True`), que varre o disco inspecionando 177 pacotes instalados no ambiente virtual (incluindo módulos web e de IA);
3. A importação estática e antecipada (eager imports) de todo o grafo de módulos do editor no topo de `editor/main.py`;
4. A instanciação síncrona antecipada de componentes pesados (como o editor de mapas e o painel de curadoria de betas) durante o `__init__` de `JanelaPrincipal`.

Como o editor é distribuído aos usuários finais empacotado em contêiner MSIX (via Microsoft Store e AppInstaller), a restrição histórica de gerar um executável único (`onefile`) não se aplica mais: o próprio contêiner MSIX instala os arquivos de forma descompactada no disco.

## Goals / Non-Goals

**Goals:**
- Reduzir o tempo de aparecimento da primeira interface gráfica para menos de 1 segundo (tanto no executável instalado quanto em desenvolvimento local via `uv run`).
- Migrar o build do PyInstaller para o modo diretório (`onedir`) sem compressão UPX em tempo de execução, integrando-o perfeitamente ao pipeline de release MSIX.
- Eliminar o overhead de descoberta de integrações do Sentry com `auto_enabling_integrations=False`, reduzindo a telemetria a um custo de inicialização desprezível (~30ms).
- Reestruturar o ponto de entrada `editor/main.py` com importações sob demanda (lazy imports), garantindo que a primeira janela (`TelaDeCarregamento` ou `JanelaPrincipal`) seja exibida imediatamente após a instanciação do `QApplication`.
- Implementar carregamento sob demanda (lazy loading) para o `WidgetEditorMapas` e evitar instanciação prematura de abas desativadas na `JanelaPrincipal`.

**Non-Goals:**
- Não alterar a lógica de sincronização remota Git ou o fluxo assíncrono de autenticação Supabase após a exibição da tela de abertura.
- Não refatorar a arquitetura interna do compilador protobuf ou da manipulação de imagens.
- Não remover recursos ou dependências legítimas do ecossistema do editor, apenas adiar o momento de seu carregamento.

## Decisions

### 1. PyInstaller `onedir` sem UPX integrado ao MSIX
- **Decisão**: Alterar `editor/EditorAresta.spec` para utilizar o padrão `COLLECT(...)`, gerando a pasta de distribuição `editor/dist/EditorAresta/`. Desativar `upx=False` tanto no `EXE` quanto no `COLLECT`. Atualizar `editor/build.py` para validar e suportar o modo `onedir`. Atualizar `.github/workflows/release-editor.yml` para copiar a pasta inteira para a área de staging do MSIX.
- **Racional**: No modo `onefile`, a cada execução o sistema extrai 118MB para `%TEMP%\_MEIxxxxxx`, gerando retenção pelo Windows Defender. No contêiner MSIX, os arquivos são descompactados uma única vez na instalação, permitindo que o executável carregue as DLLs diretamente da pasta de instalação via memória mapeada no SO em menos de 0,3s.
- **Alternativas consideradas**:
  - *Manter `onefile` desativando UPX*: Ainda exigiria a extração de 118MB a cada execução em `%TEMP%`, mantendo 10 a 15 segundos de latência com o antivírus.
  - *Criar um instalador Inno Setup clássico*: Desnecessário e incompatível com o ecossistema existente de assinatura e distribuição MSIX/AppInstaller já configurado no projeto.

### 2. Desativação de Integrações Automáticas no Sentry
- **Decisão**: Configurar `sentry_sdk.init(..., auto_enabling_integrations=False)` em `editor/core/telemetria.py`.
- **Racional**: O Sentry por padrão examina todos os módulos instalados no `sys.path` (Django, Flask, SQLAlchemy, OpenAI, LangChain, etc.) para habilitar interceptadores web. Em um ambiente desktop PyQt6, essas integrações são inúteis. A desativação reduz o tempo de `sentry_sdk.init()` de 3,5–5,5 segundos para 0,030 segundos (30ms).
- **Alternativas consideradas**:
  - *Mover a inicialização do Sentry para uma thread em segundo plano*: Poderia perder exceções que ocorram durante o arranque inicial do `QApplication` e introduzir condições de corrida nos hooks globais de erro (`sys.excepthook`). Manter síncrono com `auto_enabling_integrations=False` é determinístico e atinge 30ms sem nenhum risco de concorrência.

### 3. Reordenação do Ciclo de Boot e Lazy Imports em `editor/main.py`
- **Decisão**: Limpar os imports no nível do módulo em `editor/main.py`, mantendo apenas módulos padrão essenciais (`sys`, `os`, `signal`, `logging`) e `QApplication` do `PyQt6.QtWidgets`. A instanciação de `QApplication` e a chamada rápida de `inicializar_telemetria()` ocorrem imediatamente. As ramificações de execução carregam suas dependências sob demanda:
  - *Modo Local*: importa `JanelaPrincipal` e o workspace local, exibindo a janela diretamente.
  - *Modo Padrão*: importa `TelaDeCarregamento` e o orquestrador de inicialização, exibindo a splash screen antes de iniciar os workers de rede/git.
- **Racional**: Permite que o loop de eventos e a primeira janela gráfica surjam na tela em menos de 500ms no ambiente de desenvolvimento (`uv run`).
- **Alternativas consideradas**:
  - *Módulos lazy automáticos via `importlib`*: Introduz complexidade desnecessária e comportamento implícito ("código esperto" violando o Princípio VI). Imports locais explícitos no escopo das funções são idiomáticos em Python, simples e fáceis de rastrear.

### 4. Carregamento Sob Demanda (Lazy Loading) do Editor de Mapas na `JanelaPrincipal`
- **Decisão**: Em `editor/legacy_views/area_principal.py`, atrasar a instanciação do `WidgetEditorMapas` na `PaginaMapas` até que a aba correspondente receba foco pela primeira vez. Suprimir a instanciação do `PainelCuradoria` na `PaginaBetas` enquanto a aba de betas estiver oculta.
- **Racional**: A maioria das sessões de edição foca na aba "Dados" ou "Imagens". Instanciar a cena gráfica e canvas de mapas antecipadamente adiciona cerca de 0,5s de atraso desnecessário à abertura de qualquer croqui.
- **Alternativas consideradas**:
  - *Instanciar widgets em thread de fundo*: O framework Qt exige que todos os `QWidget` e objetos com interface gráfica sejam criados e manipulados exclusivamente na GUI thread principal. Portanto, lazy loading no evento de ativação de aba é a única abordagem segura e padronizada.

## Risks / Trade-offs

- **[Risco] Quebra do empacotamento MSIX se caminhos de arquivos relativos forem alterados no modo `onedir`** → *Mitigação*: `editor/build.py` e `editor/core/caminhos.py` já utilizam resolução baseada em `sys.frozen` e `sys._MEIPASS` ou diretório do executável (`sys.executable`). O teste unitário e a verificação do workflow garantem que os caminhos para `logo_app.png` e ícones permaneçam íntegros.
- **[Risco] Exceções não capturadas no Sentry devido à desativação de integrações** → *Mitigação*: As integrações desativadas afetam apenas frameworks web/server e IA. A captura de exceções globais (`sys.excepthook`, `threading.excepthook`, logs estruturados locais e breadcrumbs) continua 100% ativa e testada em `editor/core/telemetria_test.py`.
- **[Risco] Atraso perceptual (micro-stutter) na primeira vez que o usuário clica na aba "Mapas"** → *Mitigação*: A instanciação do `WidgetEditorMapas` leva cerca de 0,4s em máquinas de teste, o que é quase imperceptível em um clique deliberado do usuário em comparação com o atraso síncrono que ocorria na inicialização de todo croqui.

## Migration Plan

1. Atualizar e testar `editor/core/telemetria.py` com `auto_enabling_integrations=False` e garantir 100% de cobertura de testes unitários.
2. Atualizar e testar `editor/main.py` com lazy imports no boot e testes correspondentes.
3. Atualizar e testar `editor/legacy_views/area_principal.py` com lazy loading de mapas e supressão de abas ocultas.
4. Atualizar `editor/EditorAresta.spec` e `editor/build.py` para modo `onedir` sem UPX, acompanhado de `editor/build_test.py` com 100% de cobertura.
5. Atualizar `.github/workflows/release-editor.yml` para copiar a pasta `editor/dist/EditorAresta/*` no staging do MSIX.
6. Validar a inicialização ponta a ponta e submeter o PR.
