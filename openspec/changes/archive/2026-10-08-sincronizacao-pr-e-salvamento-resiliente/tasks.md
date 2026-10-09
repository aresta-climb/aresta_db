# Tasks

## 1. Salvamento Resiliente e Desacoplamento da Compilação

- [x] 1.1 Adicionar testes unitários em `editor/core/workspace_test.py` cobrindo o tratamento de exceção em `processar_renomeacao_e_compilacao` quando a compilação retorna erros e verificar que as mensagens são retornadas sem propagar `RuntimeError`.
- [x] 1.2 Atualizar `ExperimentalWorkspace` e `LocalRepoWorkspace` em `editor/core/workspace.py` para capturar exceções de compilação em `compilar_croqui`/`deploy` e retornar as mensagens de erro na tupla de resultado.
- [x] 1.3 Adicionar testes em `editor/core/worker_test.py` para `TarefaSalvamento` garantindo que o sinal `sucesso` seja emitido com as mensagens de erro de compilação sem disparar o sinal `erro`.
- [x] 1.4 Ajustar `TarefaSalvamento` em `editor/core/worker.py` para emitir `sucesso` mesmo quando houver avisos ou erros de compilação, reservando o sinal `erro` estritamente para falhas reais de I/O em disco.
- [x] 1.5 Atualizar os testes em `editor/legacy_views/area_principal_test.py` para verificar que `_on_salvar_sucesso` define `setClean()` na pilha de histórico e entrega as mensagens ao `CompilacaoController` mesmo na presença de erros.

## 2. Publicação com Confirmação para Croquis com Erro

- [x] 2.1 Adicionar testes em `editor/controllers/publish_controller_test.py` cobrindo o cenário em que `_validar_compilacao_limpa` exibe diálogo de confirmação ao encontrar erros de compilação e respeita a escolha do usuário (aceitar vs cancelar).
- [x] 2.2 Modificar `_validar_compilacao_limpa` em `editor/controllers/publish_controller.py` para substituir o bloqueio crítico por diálogo de confirmação explicativo que permite prosseguir caso o usuário confirme o envio.
- [x] 2.3 Executar a suíte de testes de `publish_controller_test.py` e verificar 100% de aprovação.

## 3. Mecânica de Sincronização Remota da Pull Request

- [x] 3.1 Criar testes em `editor/core/servico_submissao_test.py` cobrindo a detecção de novidades remotas na branch da PR (`fetch` e comparação de commits).
- [x] 3.2 Implementar método `verificar_atualizacoes_remotas_pr` em `editor/core/servico_submissao.py` utilizando `pygit2` para buscar a branch remota e comparar referências.
- [x] 3.3 Adicionar testes em `editor/core/servico_submissao_test.py` para a mesclagem automática sem conflitos (fast-forward / 3-way merge limpo) e sincronização com a pasta `database/`.
- [x] 3.4 Implementar rotina de merge automático em `editor/core/servico_submissao.py` aplicando os arquivos mesclados na pasta do croqui experimental quando não houver conflitos.
- [x] 3.5 Adicionar testes para resolução de conflitos gerando commits de merge com duplo parentesco (*ours* vs *theirs*) em `editor/core/servico_submissao_test.py`.
- [x] 3.6 Implementar rotina de resolução forçada no Git em `editor/core/servico_submissao.py` criando o commit de merge correspondente e atualizando a árvore de trabalho.
- [x] 3.7 Criar `TarefaSincronizacaoPR` em `editor/core/worker.py` com sinais de progresso, sucesso, aviso e conflito, acompanhada de testes unitários em `editor/core/worker_test.py`.

## 4. Interface de Sincronização e Diálogo de Conflitos

- [x] 4.1 Criar o diálogo `DialogoConflitoSincronizacao` em `editor/views/dialogos/dialogo_conflito_sincronizacao.py` com as opções "Manter Minha Versão Local", "Usar Versão do GitHub" e "Cancelar", acompanhado de testes em `editor/views/dialogos/dialogo_conflito_sincronizacao_test.py`.
- [x] 4.2 Adicionar a ação `acao_sincronizar` à barra superior em `editor/legacy_views/area_principal.py`, conectando o botão ao fluxo de sincronização e controlando sua habilitação.
- [x] 4.3 Integrar a checagem de sincronização automática ao carregar o croqui e antes do despacho em `PublishController`.
- [x] 4.4 Adicionar testes em `editor/legacy_views/area_principal_test.py` cobrindo o acionamento do botão de sincronização e a exibição do diálogo em caso de conflito.

## 5. Verificação e Testes de Integração

- [x] 5.1 Criar teste de integração fim-a-fim em `editor/core/sincronizacao_pr_integracao_test.py` simulando o ciclo completo: salvamento com erros de compilação, envio de PR com confirmação e sincronização bidirecional de commits remotos.
- [x] 5.2 Executar a suíte de testes completa do editor (`pytest tests/ editor/`) garantindo cobertura de 100% e ausência de regressões.
