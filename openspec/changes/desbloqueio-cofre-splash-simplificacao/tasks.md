# Tasks

## 1. Simplificação do PortalKeyring e Remoção de Timeouts Artificiais

- [x] 1.1 Atualizar `PortalKeyring._call_retrieve_secret` e `get_master_key` em `editor/plataforma/linux/portal_keyring.py` para aguardar o sinal D-Bus `Response` sem impor timeout artificial de cliente (`timeout=None`), simplificando o fluxo de leitura do pipe Unix e garantindo que o diálogo do sistema operacional não seja abortado pelo cliente Python. Verificar via testes unitários.
- [x] 1.2 Atualizar e expandir os testes em `editor/plataforma/linux/portal_keyring_test.py` cobrindo cenários de sucesso interativo, cancelamento imediato pelo usuário e leitura de segredo, verificando aprovação com 100% de cobertura de código e branches.

## 2. Inicialização Única no GerenciadorSessao (Once-and-Done)

- [x] 2.1 Refatorar `editor/core/gerenciador_sessao.py` para eliminar chamadas síncronas de I/O em `__init__`, introduzir o método explícito `inicializar_cofre() -> bool` e consolidar o estado de disponibilidade em memória para que chamadas subsequentes (`salvar_sessao`, `obter_sessao`, `cofre_disponivel`) não disparem novas consultas ao D-Bus. Verificar via testes unitários.
- [x] 2.2 Atualizar `editor/core/gerenciador_sessao_test.py` para cobrir o construtor puro, a chamada única de `inicializar_cofre()` e os fluxos de persistência e fallback, verificando 100% de cobertura.

## 3. Etapa Formal de Cofre na TarefaInicializacao e Splash Screen

- [x] 3.1 Atualizar `TarefaInicializacao.run()` em `editor/core/worker.py` para introduzir a etapa formal de acesso ao cofre de credenciais aos 15% de progresso, emitindo o status `"Acessando cofre de senhas do aplicativo..."`, aplicando pausa suave de 1.0s para leitura e invocando `gerenciador_sessao.inicializar_cofre()` em segundo plano na thread de inicialização. Verificar via testes de worker.
- [x] 3.2 Atualizar `editor/views/tela_de_abertura.py` para exibir o banner explicativo de sessão temporária em memória RAM apenas quando o cofre for explicitamente cancelado ou não inicializado. Verificar via testes unitários.
- [x] 3.3 Atualizar os testes em `editor/core/worker_test.py` e `editor/views/tela_de_abertura_test.py` cobrindo a nova sequência de inicialização e o banner de cancelamento, verificando aprovação com 100% de cobertura.

## 4. Verificação Geral e Regressão

- [x] 4.1 Executar a suíte completa de testes do projeto (`uv run pytest`) e relatório de cobertura (`coverage report`), garantindo que todos os testes passem sem regressões e com 100% de cobertura nos arquivos modificados.
