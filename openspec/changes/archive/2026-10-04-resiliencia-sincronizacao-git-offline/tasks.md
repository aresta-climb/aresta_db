# Tasks

## 1. Tratamento de Exceções e Credenciais no GerenciadorSincronizacao (`sync.py`)

- [x] 1.1 Escrever testes unitários em `editor/core/sync_test.py` para a nova exceção `ErroSincronizacaoGit`, tradução da mensagem críptica `GitError: no error`, uso de `pygit2.Passthrough` em `ChamadasGit.credentials` e deduplicação de remotes no fetch
- [x] 1.2 Implementar a exceção `ErroSincronizacaoGit` e ajustar `ChamadasGit.credentials` em `editor/core/sync.py` para lançar `raise pygit2.Passthrough()` quando `self.token` for nulo, verificando via `pytest editor/core/sync_test.py`
- [x] 1.3 Implementar a captura e tradução de `pygit2.GitError` em `clonar()` e `fazer_fetch()` em `editor/core/sync.py`, convertendo `"no error"` em diagnóstico claro de tempo limite de rede ou SSL
- [x] 1.4 Deduplicar remotes por URL em `fazer_fetch()` em `editor/core/sync.py` e validar 100% de cobertura de código em `editor/core/sync_test.py`

## 2. Resiliência e Modo Offline na TarefaInicializacao (`worker.py`)

- [x] 2.1 Escrever testes unitários em `editor/core/worker_test.py` cobrindo o cenário em que `fazer_fetch` falha com base local pré-existente (deve emitir aviso e concluir com sucesso) e quando `clonar` falha em base limpa (deve emitir erro crítico)
- [x] 2.2 Desacoplar o envio de `token_github` da sessão do usuário na instanciação do `GerenciadorSincronizacao` em `editor/core/worker.py` para operações de leitura do repositório público
- [x] 2.3 Implementar o encapsulamento resiliente de `fazer_fetch()` e `fazer_checkout_main_upstream()` em `editor/core/worker.py`, emitindo status informativo de modo offline e permitindo a conclusão da inicialização
- [x] 2.4 Executar `pytest editor/core/worker_test.py` e garantir 100% de cobertura nos cenários modificados

## 3. Validação Integrada e Verificação Geral

- [x] 3.1 Executar a suíte de testes completa do editor (`pytest editor/`) garantindo conformidade com os princípios de engenharia
- [x] 3.2 Executar `openspec validate resiliencia-sincronizacao-git-offline --strict` e verificar conformidade das especificações
