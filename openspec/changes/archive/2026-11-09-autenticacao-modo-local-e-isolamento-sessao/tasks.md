# Tasks

## 1. Biblioteca `CofreChaveiroFake` e Isolamento Global de Ambiente (`conftest.py`)

- [x] 1.1 Escrever testes comportamentais em `editor/core/gerenciador_sessao_fake_test.py` (ciclo Red) e implementar `CofreChaveiroFake` em `editor/core/gerenciador_sessao_fake.py` herdando de `keyring.backend.KeyringBackend` com suporte em memória a `get_password`, `set_password`, `delete_password` e simulação determinística de falhas (`erro_leitura`, `erro_escrita`, `erro_delecao`), verificando 100% de cobertura com `uv run pytest editor/core/gerenciador_sessao_fake_test.py --cov=editor.core.gerenciador_sessao_fake`.
- [x] 1.2 Adicionar fixture `autouse=True` em `conftest.py` que instala uma instância limpa de `CofreChaveiroFake` no `keyring` e redireciona `ARESTA_DIRETORIO_DADOS` para um diretório temporário isolado em cada teste, verificando o isolamento em `tests/conftest_teardown_test.py` com `uv run pytest tests/conftest_teardown_test.py`.
- [x] 1.3 Refatorar `editor/core/gerenciador_sessao_test.py` e `editor/core/servidor_celular_test.py` para utilizar `CofreChaveiroFake` e `GerenciadorSessaoFake` em vez de `unittest.mock.patch` sobre `keyring`, verificando 100% de cobertura com `uv run pytest editor/core/gerenciador_sessao_test.py editor/core/servidor_celular_test.py --cov=editor.core.gerenciador_sessao --cov=editor.core.servidor_celular`.

## 2. Fail-Fast no `ServidorCelular`, `TarefaDadosConexao` e `DialogoConexaoCelular`

- [x] 2.1 Atualizar testes em `editor/core/servidor_celular_test.py` (ciclo Red) e remover o fallback silencioso `http://<ip>:<porta>` em `ServidorCelular.obter_url_previa_canonica()` (`editor/core/servidor_celular.py`), lançando `RuntimeError` explícito quando não houver sessão/código válido no Cloudflare Relay, verificando 100% de cobertura com `uv run pytest editor/core/servidor_celular_test.py --cov=editor.core.servidor_celular`.
- [x] 2.2 Escrever testes em `editor/core/worker_test.py` e `editor/legacy_views/dialogo_conexao_celular_test.py` (ciclo Red) e implementar o sinal `erro = Signal(str)` em `TarefaDadosConexao` (`editor/core/worker.py`) e a exibição de erro explícito em `DialogoConexaoCelular` (`editor/legacy_views/dialogo_conexao_celular.py`), verificando 100% de cobertura nesses módulos com `uv run pytest editor/core/worker_test.py editor/legacy_views/dialogo_conexao_celular_test.py`.

## 3. Autenticação Unificada no Modo Local (`TarefaInicializacao` e `ControladorAplicativo`)

- [x] 3.1 Escrever testes em `editor/core/worker_test.py` (ciclo Red) e adicionar o parâmetro `sincronizar_git: bool = True` em `TarefaInicializacao` (`editor/core/worker.py`) para permitir validar pastas, cofre e sessão Supabase (solicitando login na UI se necessário) sem executar atualização da loja nem sincronização Git do repositório base quando `sincronizar_git=False`, verificando 100% de cobertura com `uv run pytest editor/core/worker_test.py --cov=editor.core.worker`.
- [x] 3.2 Escrever testes em `editor/main_test.py` (ciclo Red) e unificar o fluxo de Modo Local no `ControladorAplicativo` e `main()` (`editor/main.py`) via parâmetro `caminho_croqui_local: Path | None = None`, abrindo a `JanelaPrincipal` com `LocalRepoWorkspace` e `auth=self.tarefa.gerenciador_sessao` logo após o sucesso da autenticação sem abrir a `TelaDeCarregamento`, verificando 100% de cobertura com `uv run pytest editor/main_test.py --cov=editor.main`.

## 4. Verificação de Integração, Qualidade e Especificações

- [x] 4.1 Validar a change no OpenSpec com `openspec validate "autenticacao-modo-local-e-isolamento-sessao" --strict` e executar a suíte completa de testes e linters (`uv run ruff check .`, `uv run mypy` nos módulos afetados e `uv run pytest`) garantindo zero regressões e 100% de cobertura nos arquivos modificados.
