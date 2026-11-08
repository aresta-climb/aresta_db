# Design

## Context

Conforme motivado em `proposal.md`, o Editor Aresta (`editor/`) precisa de uma infraestrutura determinística de testes exploratórios caóticos e fuzzing de entradas ("Robô Caótico") capaz de exercitar 100% do ciclo de vida da aplicação em PySide6 (`QT_QPA_PLATFORM="offscreen"`), sem tocar na rede ou nos diretórios reais do sistema operacional do usuário.

Atualmente:
1. O ambiente de testes já roda headless via `editor/conftest.py` (`QT_QPA_PLATFORM="offscreen"`).
2. `obter_diretorio_base_app()` em `editor/core/storage.py` consulta diretamente o sistema operacional, e `GerenciadorSincronizacao` em `editor/core/sync.py` aponta fixamente para `https://github.com/aresta-climb/aresta_db.git`.
3. `JanelaPrincipal` instancia diretamente `ServicoSubmissao` (em `sincronizar_croqui` e via `PublishController`) e `ServidorCelular` (que abre sockets para `8.8.8.8:80`, `https://previa.arestaclimb.com/sessoes` e `wss://previa.arestaclimb.com/ws/editor`).
4. No PySide6, exceções levantadas dentro de slots Qt conectados a sinais não se propagam para o chamador de `QTest.mouseClick`, caindo em `sys.excepthook`, e diálogos modais (`.exec()`) iniciam loops de eventos aninhados bloqueantes.

## Goals / Non-Goals

**Goals:**
- Redirecionar toda a estrutura de diretórios da instalação (`ARESTA_DIRETORIO_DADOS`) e o repositório Git upstream (`ARESTA_GIT_UPSTREAM_URL`) para `tmp_path`, permitindo que `pygit2` execute `clonar()`, `fazer_fetch()` e `checkout` reais localmente em milissegundos.
- Prover bibliotecas `test-only` de Fakes determinísticos testadas (`*_fake.py` + `*_fake_test.py`) para as 5 fronteiras de nuvem/SO (`ClienteAuthSupabaseFake`, `GerenciadorSessaoFake`, `ServicoSubmissaoFake`, `ServidorCelularFake`, `AdaptadorPlataformaFake`) e um bloqueador hard de rede no nível de `socket` (`BloqueadorRedeCaos`).
- Implementar `MotorRoboCaoticoQt` com **Orçamento Ponderado** (10–15% dos passos no fluxo de entrada `TelaDeAbertura` -> `TelaDeCarregamento`, 85–90% na `JanelaPrincipal` e seus diálogos), interceptador automático de modais (`QApplication.activeModalWidget()`) e **3 Oráculos de Falha** (Exceções/C++, Simetria de Undo/Redo e Integridade do Diário).
- Implementar o encolhedor de caminhos por busca binária (`EncolhedorCaminhoCrash` / `ddmin`), serialização em JSON (`ReceitaCrashRobo`), campanha de 5 minutos com deduplicação no `release-editor.yml` e envio de falhas inéditas ao Sentry com `contexts.receita_robo_caotico`.

**Non-Goals:**
- Substituir os testes unitários e de integração comportamentais 1:1 exigidos pelo `AGENTS.md`.
- Utilizar `unittest.mock`, `MagicMock` ou `patch` para isolar classes ou modelos internos do projeto (estritamente proibido pelo Princípio V do `AGENTS.md`).

## Decisions

### 1. Isolamento Total em `tmp_path` com Git "Upstream" Local Real + Fakes de Fronteira
- **Decisão**:
  1. Em `editor/core/storage.py`, `obter_diretorio_base_app()` verifica primeiro `os.environ.get("ARESTA_DIRETORIO_DADOS")` e `GerenciadorCaminhos.__init__(self, diretorio_base: Path | None = None)` aceita um diretório explícito.
  2. Em `editor/core/sync.py`, `GerenciadorSincronizacao.obter_url_clone()` e `configurar_remotes()` respeitam `os.environ.get("ARESTA_GIT_UPSTREAM_URL")` quando definido.
  3. A `FabricaDatasetCaos` cria em `tmp_path/remoto_oficial.git` um repositório Git real via `pygit2` com commit na branch `main` contendo `database/croqui_normal/` e `database/croqui_toxico/`. Assim, `TarefaInicializacao` roda o código real de clone e fetch via `pygit2` no disco local sem precisar de Fake para `GerenciadorSincronizacao`.
  4. Para as 5 fronteiras que sairiam para serviços externos ou recursos globais do SO, criamos Fakes determinísticos de primeira classe:
     - `editor/core/cliente_auth_supabase_fake.py` (`ClienteAuthSupabaseFake`)
     - `editor/core/gerenciador_sessao_fake.py` (`GerenciadorSessaoFake`)
     - `editor/core/servico_submissao_fake.py` (`ServicoSubmissaoFake`, que reutiliza a comparação de arquivos reais contra o repo Git local em `tmp_path` e simula o envio REST/Git-Proxy e respostas `ATUALIZADO`, `MESCLADO` e `CONFLITO`)
     - `editor/core/servidor_celular_fake.py` (`ServidorCelularFake`, `QObject` com sinal `dispositivo_conectado`, geração real de QR Code PNG em memória e registro de `emitir_recarregamento`, sem abrir `uvicorn`, `8.8.8.8` ou `previa.arestaclimb.com`)
     - `editor/plataforma/adaptador_plataforma_fake.py` (`AdaptadorPlataformaFake`)
- **Racional**: Maximiza a quantidade de código real exercitado (incluindo `pygit2`, compilação, diário binário e geração de QR Code) enquanto garante execução determinística em `< 20ms` de setup e zero efeitos colaterais no SO ou na rede.
- **Alternativas consideradas**:
  - *Criar um `GerenciadorSincronizacaoFake` que não usa `pygit2`*: Rejeitado porque o `pygit2` clona repositórios locais em `tmp_path` nativamente e de forma quase instantânea, permitindo testar o código real de `sync.py` e `croqui_experimental.py`.

### 2. Guardião de Bloqueio de Rede (`BloqueadorRedeCaos`)
- **Decisão**: Implementar um gerenciador de contexto em `editor/caos/bloqueador_rede.py` que intercepta `socket.socket.connect`, `socket.socket.connect_ex`, `socket.create_connection` e `QDesktopServices.openUrl`.
  - Conexões para endereços que não sejam loopback (`127.0.0.1`, `::1`, `localhost`) ou sockets Unix locais lançam `ErroAcessoRedeProibidoEmTeste`.
  - Aberturas de URL externa em `QDesktopServices.openUrl` são interceptadas e registradas em memória sem abrir o navegador do sistema operacional.
  - Quando `REPORTAR_SENTRY_CAOS=1` estiver ativo, o bloqueador permite abrir uma janela controlada exclusivamente durante a chamada `capturar_crash_robo_caotico` após o término do shrinking.
- **Racional**: Garante que qualquer nova feature futura que tente acessar a internet sem passar por um Fake falhe imediatamente durante os testes.

### 3. Seletores Semânticos Resilientes (`SeletorAlvoQt` e `PassoRobo`)
- **Decisão**: Cada passo (`PassoRobo`) é imutável e serializável em JSON, identificando o alvo na interface Qt através de uma hierarquia semântica (`SeletorAlvoQt`):
  1. `acao_toolbar`: Nome/texto ou tooltip de `QAction` em `QToolBar` (`"Salvar"`, `"Desfazer"`, `"Refazer"`, `"Dados"`, `"Imagens"`, `"Mapas"`, `"Betas"`, `"Propor Mudança"`, `"Sincronizar"`, `"Celular"`, `"Abrir Novo"`).
  2. `caminho_no_arvore`: Caminho lógico no `TreeViewAdapter` (ex: `"croqui/expando:picos/item:0/expando:setores_ou_grupos/item:0"`), permitindo selecionar, expandir ou acionar botões inline do nó na `QTreeView`.
  3. `campo_formulario`: Rótulo do `QFormLayout` + classe do widget (`QLineEdit`, `QTextEdit`, `QComboBox`, `QSpinBox`, `QDoubleSpinBox`, `QCheckBox`, `WidgetCampoCoordenadaE7`) + índice de ocorrência.
  4. `objeto_ou_texto`: `objectName()` ou combinação `classe + text()/toolTip() + indice` dentro da janela ou `QDialog` modal ativo.
  5. `cena_grafica`: Alvo de canvas (`"mapa_cena"` ou `"imagem_canvas"`) com operação parametrizada (`clique`, `arraste_retangulo`, `traco_polilinha`, `slider_bulk`).
- **Racional**: Torna as receitas `.json` em `editor/caos/caminhos_regressao/` legíveis por humanos e agentes e imunes a variações de coordenadas de pixel entre Windows, Linux (`xvfb`) e macOS.

### 4. Desbloqueio de Diálogos Modais (`QDialog.exec()`) e Captura de Exceções em Slots
- **Decisão**:
  1. **Interceptação de Modais**: Antes de despachar uma ação que pode abrir um diálogo modal bloqueante (`.exec()`), o `MotorRoboCaoticoQt` mantém um `QTimer` de vigilância ativo (`intervalo=15ms`). Quando `QApplication.activeModalWidget()` (ou `activePopupWidget()`) detecta um `QDialog` / `QMessageBox` / `QInputDialog` visível:
     - O timer executa de 1 a 4 sub-passos determinísticos (guiados pelo mesmo `Random(seed)`) preenchendo widgets internos do diálogo (`QLineEdit`, `QComboBox`, `QListWidget`, botões de decisão de conflito) e, ao final, aciona o botão de confirmação (`accept` / `Yes` / `Save` / `Discard`) ou cancelamento (`reject` / `Cancel`), encerrando o loop aninhado do `.exec()` e devolvendo o controle ao passo principal.
  2. **Captura de Exceções**: O motor substitui temporariamente `sys.excepthook` e `threading.excepthook` durante cada passo e aguarda a conclusão de `QThread`s ativas de curta duração (como `TarefaSalvamento`, `TarefaPublicacao`, `TarefaSincronizacaoPR`), coletando qualquer exceção ocorrida na thread principal ou em workers.

### 5. Os 3 Oráculos de Falha (`OraculosCaos`)
- **Decisão**: Ao final de cada `PassoRobo` (e após o fechamento de eventuais modais e conclusão de salvamento pendente), `OraculosCaos` verifica:
  1. **Oráculo de Exceções e C++**: Verifica se alguma exceção foi capturada no hook global ou se a janela principal perdeu integridade estrutural inesperadamente.
  2. **Oráculo de Simetria de Undo/Redo e Princípio VIII**:
     - Mantém um dicionário `hashes_por_indice: dict[int, bytes]` mapeando `pilha_undo.index() -> sha256(croqui_proto.SerializeToString(deterministic=True))`.
     - Se uma ação de UI (fora de salvamento/sincronização que recarrega o modelo) alterar o hash do Protobuf **sem** alterar o `index()` (ou sem atualizar o comando topo com `mergeWith` legítimo registrado), ou se um `Undo`/`Redo` para um índice $k$ já visitado produzir um hash diferente de `hashes_por_indice[k]`, o oráculo dispara `ErroViolacaoSimetriaUndoRedo` apontando o comando no topo da pilha!
     - Quando um salvamento (`_on_salvar_sucesso`) ou sincronização recarrega/normaliza UIDs do banco, a tabela `hashes_por_indice` é ressincronizada no índice atual.
  3. **Oráculo de Integridade do Diário (`GerenciadorDiario`)**:
     - Verifica se `diario.ler_diario_pendente()` e `diario.ler_diario_salvo()` executam sem levantar exceções de corrupção binária ou Protobuf truncado.

### 6. Shrinking (`ddmin`), Campanha de 5 Minutos e Integração Sentry
- **Decisão**:
  - `EncolhedorCaminhoCrash` aplica *Delta Debugging* (`ddmin` por busca binária com `max_tentativas=12`), reexecutando candidatos em um `tmp_path` limpo recriado pela `FabricaDatasetCaos` com a mesma `seed` de dataset. Passos cujo alvo não exista na tela durante uma tentativa de poda são ignorados como `no-op` e removidos da receita mínima final caso a mesma falha se repita.
  - Em `.github/workflows/release-editor.yml`, reordenamos o job `prepare_release` para instalar as dependências gráficas, rodar `pytest` e rodar a campanha de 5 minutos (`DURACAO_CAMPANHA_CAOS_SEGUNDOS=300`, `REPORTAR_SENTRY_CAOS=1`) **antes** do step `Injetar Versão Oficial` (`git commit` / `git tag`).

## Risks / Trade-offs

- **[Risco] Workers assíncronos (`TarefaSalvamento`, `TarefaSincronizacaoPR`) ainda rodando quando o próximo passo começa ou quando a janela fecha** → **Mitigação**: O motor aguarda de forma determinística (com timeout curto de segurança) a finalização de `_worker_salvar` / `_tarefa_sincronizacao` quando o passo aciona salvamento/sincronização, ou exercita propositalmente cliques durante o salvamento e garante no teardown do teste que todas as `QThread`s finalizaram (`wait(2000)`).
- **[Risco] Coalescência de comandos de edição de texto (`mergeWith` no `QUndoCommand`) alterar o Protobuf mantendo o mesmo `pilha.index()`** → **Mitigação**: O Oráculo de Simetria distingue entre: (a) o índice da pilha não mudou porque um comando foi mesclado no comando do topo (`pilha.index() > 0` durante edição contínua do mesmo campo, atualizando o hash do índice topo `k`, mas preservando intocado o hash de `k - 1` que será verificado no `Undo`), e (b) o retorno via `Undo` para `k - 1`, que exige igualdade exata byte-a-byte com o estado anterior ao comando!
