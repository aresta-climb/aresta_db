# Proposal

## Why

Ao iniciar o Editor Aresta em Modo Local (`uv run editor/main.py database/<id>`), o fluxo de inicialização pulava a verificação de autenticação e o desbloqueio do cofre de credenciais, abrindo a `JanelaPrincipal` sem sessão válida caso o usuário não estivesse autenticado. Paralelamente, testes da suíte (`gerenciador_sessao_test.py` e `servidor_celular_test.py`) vazavam chamadas para o Keyring real do sistema operacional e para `%APPDATA%\Editor Aresta`, apagando a sessão real do desenvolvedor a cada execução do `pytest`, e o `ServidorCelular` degradava silenciosamente para um IP local sem código de pareamento (`---- - ----`) nem túnel de Live Reload quando não havia token JWT disponível.

## What Changes

- **Autenticação Unificada no Modo Local (`editor/main.py`, `editor/core/worker.py`)**: Unificação da inicialização do Modo Local dentro do `ControladorAplicativo` e `TarefaInicializacao` (com `sincronizar_git=False`), garantindo a inicialização do cofre e a validação/renovação da sessão Supabase antes de abrir o `LocalRepoWorkspace`. Caso já exista sessão válida, abre a `JanelaPrincipal` diretamente sem `git fetch` nem `TelaDeCarregamento`; caso não exista sessão válida, apresenta o fluxo de login na `TelaDeAbertura` e abre o croqui local imediatamente após autenticar.
- **Remoção de Fallback Silencioso no Live Review (`editor/core/servidor_celular.py`, `editor/core/worker.py`, `editor/legacy_views/dialogo_conexao_celular.py`)**: **BREAKING** (interno) Remoção do fallback silencioso em `ServidorCelular.obter_url_previa_canonica()` que retornava `http://<ip>:<porta>` sem código de sessão quando o registro no Cloudflare Relay falhava por ausência de JWT ou erro de rede. A `TarefaDadosConexao` e o `DialogoConexaoCelular` passam a falhar explicitamente (Fail-Fast), exibindo o erro na interface em vez de mostrar `---- - ----`.
- **Biblioteca `CofreChaveiroFake` e Isolamento Global de Keyring e AppData nos Testes (`editor/core/gerenciador_sessao_fake.py`, `conftest.py`)**: Criação do backend determinístico em memória `CofreChaveiroFake` (compatível com o contrato do `keyring` e configurável para simular falhas de leitura, escrita e remoção), eliminação de `unittest.mock.patch` sobre `keyring` nos testes de sessão e ativação de isolamento global automático (`autouse=True`) no `conftest.py` para o Keyring e para `ARESTA_DIRETORIO_DADOS`, impedindo que qualquer teste leia ou apague credenciais reais do desenvolvedor ou do ambiente de CI/CD.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability isolada; os requisitos evoluem capabilities existentes. -->

### Modified Capabilities
- `editor-local-mode`: Atualiza o requisito de inicialização em Modo Local para exigir sessão autenticada (reaproveitando sessão persistida ou solicitando login na `TelaDeAbertura`), mantendo o pulo da sincronização Git do repositório base e da `TelaDeCarregamento`.
- `editor-inicializacao`: Ajusta o cenário de inicialização em Modo Local e transição do `ControladorAplicativo` para suportar abertura direta de `LocalRepoWorkspace` após validação de autenticação sem sincronização Git.
- `servidor-celular`: Substitui o fallback silencioso de URL local por falha explícita (Fail-Fast) quando a criação de sessão autenticada no Cloudflare Relay falhar, reportando o erro no `DialogoConexaoCelular`.
- `isolamento-instalacao-git-e-fakes-editor`: Adiciona o requisito de isolamento global automático de Keyring (`CofreChaveiroFake`) e de diretório de dados (`ARESTA_DIRETORIO_DADOS`) no `conftest.py` para impedir vazamento de estado para o sistema operacional hospedeiro.

## Impact

- **Código de Produção**: `editor/main.py`, `editor/core/worker.py`, `editor/core/servidor_celular.py`, `editor/legacy_views/dialogo_conexao_celular.py`.
- **Bibliotecas de Fakes e Infraestrutura de Testes**: `editor/core/gerenciador_sessao_fake.py`, `editor/core/gerenciador_sessao_fake_test.py`, `conftest.py`, `editor/core/gerenciador_sessao_test.py`, `editor/core/servidor_celular_test.py`, `editor/main_test.py`, `editor/core/worker_test.py`, `editor/legacy_views/dialogo_conexao_celular_test.py`.
