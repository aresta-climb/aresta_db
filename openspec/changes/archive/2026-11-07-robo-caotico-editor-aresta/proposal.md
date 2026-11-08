# Proposal

## Why

O Editor Aresta combina árvore de dados Protobuf, formulários dinâmicos (`ProtobufWidgetFactory`), canvas vetorial 2D (`QGraphicsScene` em `WidgetEditorMapas`), editor de imagens com corte/máscara, compilação assíncrona em `QThread`, diário binário transacional (`GerenciadorDiario`) e pilha global de histórico (`QUndoStack`). Nessa superfície altamente mutável, sequências não-óbvias de interações (como editar um campo e trocar de nó na árvore antes de o timer de coalescência disparar, desenhar uma rota no mapa e desfazer/excluir a escalada em outra aba, ou receber conflito de sincronização com edições pendentes) podem causar `RuntimeError: Internal C++ object already deleted`, dessincronização entre `CroquiModel` e `QUndoStack`, corrupção do diário ou falhas de compilação que testes unitários de caminho feliz não alcançam. Precisamos de um sistema de testes exploratórios caóticos determinísticos e fuzzing de inputs ("Robô Caótico") que exercite 100% da aplicação em modo headless (`offscreen`), blinde os testes contra acessos acidentais à rede, encolha automaticamente qualquer falha até a menor sequência reproduzível (`ddmin`), reporte falhas inéditas ao Sentry e mantenha cada crash encontrado como teste de regressão permanente.

## What Changes

- **Isolamento Completo de Instalação e Git Local em `tmp_path` + Fakes Determinísticos de Fronteira Externa**:
  - Estender `obter_diretorio_base_app()` e `GerenciadorCaminhos` (`editor/core/storage.py`) para suportar redirecionamento completo das pastas da instalação (`aresta_db`, `croquis`, `diarios_locais`, `.trash_interna`) para `tmp_path` via parâmetro `diretorio_base` ou variável de ambiente `ARESTA_DIRETORIO_DADOS`.
  - Estender `GerenciadorSincronizacao` (`editor/core/sync.py`) para respeitar `ARESTA_GIT_UPSTREAM_URL` (apontando para um repositório Git bare/remoto local criado via `pygit2` em `tmp_path/remoto_oficial.git`), permitindo que `TarefaInicializacao` execute `clonar()`, `configurar_remotes()`, `fazer_fetch()` e `fazer_checkout_main_upstream()` 100% reais no disco temporário sem tocar na internet.
  - Criar bibliotecas `test-only` de Fakes determinísticos com seus respectivos testes espelhados (`*_fake.py` e `*_fake_test.py`) para as fronteiras externas de nuvem e SO: `ClienteAuthSupabaseFake`, `GerenciadorSessaoFake`, `ServicoSubmissaoFake` (usando diff Git local real e simulando criação/atualização de PR e conflitos em `sincronizar_pr_remota`), `ServidorCelularFake` (simulando pareamento Live Review, QR Code e Hot Reload sem bater em `8.8.8.8` ou `previa.arestaclimb.com`) e `AdaptadorPlataformaFake` (simulando verificação de atualização sem acionar Microsoft Store/Sparkle).
  - Permitir a injeção limpa dessas fronteiras em `ControladorAplicativo`, `TarefaInicializacao` e `JanelaPrincipal`.
- **Bloqueador Hard de Rede (`BloqueadorRedeCaos`)**:
  - Criar guardião em `editor/caos/bloqueador_rede.py` que intercepta conexões de socket (`socket.socket.connect`, `connect_ex`, `socket.create_connection`) e aberturas de navegador externo (`QDesktopServices.openUrl`), bloqueando com `ErroAcessoRedeProibidoEmTeste` qualquer tentativa de tráfego externo fora de loopback (`127.0.0.1` / `::1` / `localhost`) durante os testes.
- **Fábrica de Datasets Normal e Tóxico (`FabricaDatasetCaos`) e Gerador de Fuzz Inputs**:
  - Criar `editor/caos/fabrica_dataset_caos.py` que constrói em `tmp_path` o repositório Git "upstream" local e workspaces contendo um **Croqui Normal** (completo com picos, grupos, setores, escaladas, imagens PNG válidas, mapas e betas pendentes) e um **Croqui Tóxico de Estresse** (oneofs alternados, listas vazias e listas extensas, strings de 300+ caracteres sem espaços, emojis compostos, caracteres hostis ao YAML/Markdown como `: `, `---`, `#`, tags `<small>`, referências `[[...]]` quebradas, coordenadas E7 limítrofes e imagens com razões de aspecto extremas).
- **Motor de Robô Caótico Qt com Orçamento Ponderado e 3 Oráculos (`MotorRoboCaoticoQt`)**:
  - Criar `editor/caos/motor_robo_caotico.py` guiado por `random.Random(seed)` operando sobre toda a aplicação (`ControladorAplicativo` e `JanelaPrincipal`) com **Orçamento Ponderado**:
    - **Fase A (~10–15% dos passos)**: Travessia de entrada exercitando `TelaDeAbertura` (login OTP, `DialogoPerfilAutor`, banner de atualização) e `TelaDeCarregamento` (`DialogoNovoCroqui` com inputs fuzz, `DialogoBuscaCroqui` importando croqui oficial do Git local, exclusão de croqui do histórico e abertura na `JanelaPrincipal`).
    - **Fase B (~85–90% dos passos)**: Massacre focado na `JanelaPrincipal` (seleção/expansão/reordenação na `QTreeView`, edição fuzz nos widgets gerados por `ProtobufWidgetFactory`, troca de `oneof`, desenho/conversão/sliders no `QGraphicsScene` de `WidgetEditorMapas`, corte/máscara em `WidgetEditorImagens`, `PaginaBetas`, rajadas de `Undo`/`Redo`, `Salvar` assíncrono, `PublishDialog`, `Sincronizar` com e sem `DialogoConflitoSincronizacao`, `DialogoConexaoCelular` e retorno via `Abrir Novo`).
  - Interceptador automático de diálogos modais (`QApplication.activeModalWidget()` via `QTimer`) para interagir caoticamente com campos de qualquer `QDialog` / `QMessageBox` modal e fechá-lo (`accept`/`reject`) sem travar o loop de eventos aninhado do Qt.
  - Verificação a cada passo de **3 Oráculos de Falha**:
    1. **Exceções e C++**: Captura via `sys.excepthook` e `threading.excepthook` (incluindo `RuntimeError: Internal C++ object already deleted` e falhas em `QThread`).
    2. **Simetria de Undo/Redo e Princípio VIII**: Auditoria do hash determinístico do Protobuf (`SerializeToString(deterministic=True)`) por índice da `QUndoStack`, detectando mutações fora de `QUndoCommand` ou `undo()`/`redo()` assimétricos.
    3. **Integridade do Diário (`GerenciadorDiario`)**: Validação de leitura e desserialização sem corrupção dos arquivos `diario_pendente.bin` e `diario_salvo.bin`.
- **Encolhedor de Caminhos (`EncolhedorCaminhoCrash`), Receita JSON, CI e Sentry**:
  - Implementar *Delta Debugging* (`ddmin` por busca binária) em `editor/caos/encolhedor_caminho_crash.py` e serialização em `editor/caos/receita_crash_robo.py`, reduzindo falhas para a sequência mínima de `PassoRobo` com seletores semânticos Qt (`SeletorAlvoQt`) e salvando em `editor/caos/caminhos_regressao/`.
  - Criar a suíte rápida de regressão (`editor/caos/regressao_caminhos_test.py`) e a campanha por orçamento de tempo (`editor/caos/robo_caotico_exploratorio_test.py`) com deduplicação por assinatura (`tipo_excecao + frame_principal`).
  - Estender `editor/core/telemetria.py` (`capturar_excecao` / `capturar_crash_robo_caotico`) para anexar `contexts.receita_robo_caotico` no Sentry com nível `fatal` e atualizar a skill `diagnosticar-issue-sentry` para cobrir receitas do `aresta_db`.
  - Atualizar `.github/workflows/release-editor.yml` para executar a suíte de testes e a campanha de 5 minutos do Robô Caótico **antes** do commit e tag da versão, fazendo upload das receitas JSON como artefato caso encontre falhas.

## Capabilities

### New Capabilities
- `robo-caotico-editor-aresta`: Motor de exploração caótica determinística em PySide6 (`MotorRoboCaoticoQt`), orçamento ponderado cobrindo toda a aplicação, interceptação de modais Qt, 3 oráculos de falha (Exceções/C++, Simetria de Undo/Redo, Integridade do Diário), `FabricaDatasetCaos` (Normal e Tóxico), `BloqueadorRedeCaos`, shrinking por busca binária (`ddmin`), suíte de regressão de caminhos e campanha por tempo com deduplicação.
- `isolamento-instalacao-git-e-fakes-editor`: Redirecionamento completo dos diretórios da instalação (`ARESTA_DIRETORIO_DADOS`) e upstream Git (`ARESTA_GIT_UPSTREAM_URL`) para `tmp_path`, além das bibliotecas `test-only` de Fakes determinísticos (`ClienteAuthSupabaseFake`, `GerenciadorSessaoFake`, `ServicoSubmissaoFake`, `ServidorCelularFake`, `AdaptadorPlataformaFake`) e sua injeção de dependência no Editor.

### Modified Capabilities
- `editor-telemetria-crash`: Suporte a acoplar contextos estruturados extras (`receita_robo_caotico`) e severidade `fatal` no envio de exceções ao Sentry em `editor/core/telemetria.py`, além da atualização das instruções da skill `diagnosticar-issue-sentry` para reproduzir receitas do Editor Aresta.
- `editor-workflow-release`: Reordenação do job `prepare_release` em `.github/workflows/release-editor.yml` para validar `pytest` e executar uma campanha de 5 minutos do Robô Caótico (com reporte ao Sentry e upload de artefatos JSON) antes de realizar o commit e a tag de lançamento.

## Impact

- `editor/core/storage.py`, `editor/core/sync.py`, `editor/core/telemetria.py`, `editor/core/worker.py`, `editor/main.py`, `editor/legacy_views/area_principal.py` e respectivos arquivos `*_test.py`
- Fakes de fronteira externa e testes espelhados:
  - `editor/core/cliente_auth_supabase_fake.py` e `editor/core/cliente_auth_supabase_fake_test.py`
  - `editor/core/gerenciador_sessao_fake.py` e `editor/core/gerenciador_sessao_fake_test.py`
  - `editor/core/servico_submissao_fake.py` e `editor/core/servico_submissao_fake_test.py`
  - `editor/core/servidor_celular_fake.py` e `editor/core/servidor_celular_fake_test.py`
  - `editor/plataforma/adaptador_plataforma_fake.py` e `editor/plataforma/adaptador_plataforma_fake_test.py`
- Módulos do Robô Caótico em `editor/caos/`:
  - `bloqueador_rede.py` e `bloqueador_rede_test.py`
  - `fabrica_dataset_caos.py` e `fabrica_dataset_caos_test.py`
  - `receita_crash_robo.py` e `receita_crash_robo_test.py`
  - `encolhedor_caminho_crash.py` e `encolhedor_caminho_crash_test.py`
  - `oraculos_caos.py` e `oraculos_caos_test.py`
  - `motor_robo_caotico.py` e `motor_robo_caotico_test.py`
  - `regressao_caminhos_test.py`, `robo_caotico_exploratorio_test.py` e diretório `editor/caos/caminhos_regressao/`
- `.github/workflows/release-editor.yml`
- `.agent/skills/diagnosticar-issue-sentry/SKILL.md` e `.agents/skills/diagnosticar-issue-sentry/SKILL.md`
