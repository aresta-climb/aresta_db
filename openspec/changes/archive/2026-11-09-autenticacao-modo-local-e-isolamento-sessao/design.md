# Design

## Context

Veja `proposal.md` para a motivação completa. Atualmente:
1. Em `editor/main.py`, o tratamento de argumentos de linha de comando (`len(sys.argv) > 1`) instancia `LocalRepoWorkspace` e `JanelaPrincipal(auth=None)` diretamente na função `main()`, contornando `ControladorAplicativo` e `TarefaInicializacao`.
2. Em `editor/core/servidor_celular.py`, `obter_url_previa_canonica()` tenta `solicitar_sessao_servidor()` e, caso falhe (ex: ausência de token JWT ou erro HTTP), faz um fallback silencioso para `f"http://{ip}:{porta}"`, enquanto o túnel WebSocket (`_iniciar_tunel`) encerra silenciosamente por falta de `codigo_sessao`.
3. Em `editor/core/gerenciador_sessao_test.py` e `editor/core/servidor_celular_test.py`, testes unitários instanciam `GerenciadorSessao(usar_memoria=False)` ou `ServidorCelular(tmp_path)` sem isolamento completo do módulo `keyring`, fazendo com que `limpar_sessao()` apague a chave `chave_criptografia_sessao` do cofre real do sistema operacional e remova `%APPDATA%\Editor Aresta\.sessao_auth.enc`.

## Goals / Non-Goals

**Goals:**
- Unificar o ciclo de vida do Modo Local dentro do `ControladorAplicativo` e `TarefaInicializacao`, garantindo cofre inicializado e sessão autenticada antes de abrir a `JanelaPrincipal`.
- Manter o arranque rápido do Modo Local quando a sessão já estiver válida (pulando o `git clone`/`git fetch` do repositório base e a `TelaDeCarregamento`).
- Eliminar o fallback silencioso no `ServidorCelular` e exibir diagnóstico explícito de erro no `DialogoConexaoCelular` (Princípio VIII do `AGENTS.md`).
- Prover `CofreChaveiroFake` em `editor/core/gerenciador_sessao_fake.py` e ativar isolamento automático global de `keyring` e `ARESTA_DIRETORIO_DADOS` em `conftest.py` (Princípio V do `AGENTS.md`).

**Non-Goals:**
- Alterar o protocolo do Cloudflare Worker (`previa.arestaclimb.com`) ou o fluxo de conexão do aplicativo móvel Flutter.
- Executar sincronização Git do repositório `%APPDATA%/Editor Aresta/aresta_db` quando o editor é aberto em Modo Local.

## Decisions

### 1. Unificação do Modo Local no `ControladorAplicativo` e `TarefaInicializacao`
- **Decisão**:
  - Adicionar o parâmetro `sincronizar_git: bool = True` em `TarefaInicializacao.__init__()`. Quando `sincronizar_git=False`, a tarefa executa a inicialização de pastas, o desbloqueio do cofre (`inicializar_cofre()`, com `intervalo_espera_cofre=0.0` quando já injetado ou em modo local rápido) e a validação/renovação de sessão Supabase (solicitando login na `TelaDeAbertura` caso não haja sessão válida), mas pula a verificação de atualização da loja e a etapa 4 (`GerenciadorSincronizacao`).
  - Adicionar o parâmetro `caminho_croqui_local: Path | None = None` em `ControladorAplicativo.__init__()`. Quando `caminho_croqui_local` for fornecido:
    - `iniciar_inicializacao()` instancia `TarefaInicializacao(..., sincronizar_git=False, intervalo_espera_cofre=0.0)`.
    - O sinal `self.tarefa.sucesso` (ou o despacho em `executar_selecao()`) detecta `self._caminho_croqui_local is not None` e chama diretamente `mostrar_janela_principal()`, que instancia `LocalRepoWorkspace(self._caminho_croqui_local)` e `JanelaPrincipal(..., auth=self.tarefa.gerenciador_sessao)`.
- **Alternativas consideradas**:
  - *Pedir login apenas sob demanda ao clicar em "Conectar ao Celular"*: Descartada porque deixa o editor em estado parcialmente não autenticado durante a edição local e exigiria duplicar o fluxo de login fora da `TelaDeAbertura`.

### 2. Fail-Fast em `ServidorCelular`, `TarefaDadosConexao` e `DialogoConexaoCelular`
- **Decisão**:
  - Em `ServidorCelular.obter_url_previa_canonica()`, se não houver `url_previa_canonica`, nem `codigo_sessao`, e `solicitar_sessao_servidor()` retornar `False`, lançar `RuntimeError("Não foi possível iniciar sessão de prévia no servidor de retransmissão. Verifique sua autenticação e conexão com a internet.")` em vez de retornar `f"http://{ip}:{porta}"`.
  - Em `TarefaDadosConexao`, adicionar o sinal `erro: Signal = Signal(str)` e emitir `self.erro.emit(str(e))` quando `obter_url_previa_canonica()` falhar ou o servidor não conseguir alocar porta.
  - Em `DialogoConexaoCelular`, conectar `self.tarefa_dados.erro` ao método `_ao_erro_carregamento(mensagem: str)`, que oculta o spinner de carregamento e exibe a mensagem de erro de forma explícita e legível na área central/status do diálogo.
- **Alternativas consideradas**:
  - *Manter fallback HTTP local com aviso*: Descartada porque o aplicativo móvel e o canal de eventos de Live Reload (`emitir_recarregamento`) dependem do túnel e da descoberta via Cloudflare Relay; exibir um QR Code de IP local sem código de sessão induz o usuário ao erro.

### 3. `CofreChaveiroFake` e Guardião Global no `conftest.py`
- **Decisão**:
  - Implementar `CofreChaveiroFake` em `editor/core/gerenciador_sessao_fake.py` herdando de `keyring.backend.KeyringBackend` (implementando `priority = 10`, `get_password`, `set_password` e `delete_password` em dicionário em memória, com flags `erro_leitura`, `erro_escrita` e `erro_delecao` para simulação determinística de falhas).
  - No `conftest.py` raiz, adicionar uma fixture `autouse=True` (`_isolar_ambiente_sessao_e_dados`) que:
    1. Salva o backend original do `keyring`, instala uma instância limpa de `CofreChaveiroFake()` antes de cada teste e restaura no teardown.
    2. Define `ARESTA_DIRETORIO_DADOS` apontando para um subdiretório de `tmp_path` via `monkeypatch.setenv` (permitindo que testes específicos como `storage_test.py` façam `monkeypatch.delenv` quando testarem o fallback sem variável de ambiente).
  - Refatorar `editor/core/gerenciador_sessao_test.py` e `editor/core/servidor_celular_test.py` para usar `CofreChaveiroFake` e `GerenciadorSessaoFake`, removendo os `patch("keyring.*")`.

## Risks / Trade-offs

- **[Risco] Testes de adaptadores de plataforma (`integracao_test.py`) que inspecionam `keyring.get_keyring()`** → *Mitigação*: Esses testes já configuram ou substituem explicitamente o backend durante o ato do teste; como a fixture `autouse=True` restaura o backend no teardown de cada teste, não há interferência entre testes.
- **[Risco] Desenvolvedor abrir Modo Local totalmente offline sem sessão prévia salva** → *Mitigação*: Se já houver sessão salva no `GerenciadorSessao`, e a falha de validação ocorrer apenas por ausência de internet (erro de rede em `obter_usuario_atual`/`renovar_sessao`), podemos preservar a sessão local existente em modo offline ou exigir login apenas quando não houver credencial salva.
