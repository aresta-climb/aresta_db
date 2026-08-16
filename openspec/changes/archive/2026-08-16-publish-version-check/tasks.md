## 1. Testes de Integração e TDD Inicial (Princípios III, IV e V)

- [x] 1.1 Criar a suíte de testes unitários `editor/core/servico_loja_test.py` cobrindo via TDD:
  - **Detecção de ambiente não-Store**: validação de que quando o processo roda sem identidade de pacote MSIX (`APPMODEL_ERROR_NO_PACKAGE` / WinError 15700 ou falta de módulo WinRT), a checagem é pulada imediatamente e retorna status de bypass neutro (`nao_aplicavel`), sem gerar exceções.
  - **Consulta de atualizações na Microsoft Store**: com mock de `StoreContext` em ambiente empacotado (sem updates, update opcional, update obrigatório, falha de rede/timeout com fallback gracioso).
  - **Execução Híbrida de Instalação**:
    - Cenário de sucesso na chamada in-app `RequestDownloadAndInstallStorePackageUpdatesAsync`.
    - Cenário de fallback para abertura de `ms-windows-store://pdp/?ProductId=...` e chamada de `QApplication.quit()` quando a API WinRT falha ou não está disponível.
- [x] 1.2 Criar os testes unitários em `editor/views/tela_de_abertura_test.py` e `editor/core/worker_test.py` cobrindo:
  - **Bypass completo no Boot**: ao rodar fora da Store, a `TarefaInicializacao` pula o version check sem emitir erros e segue diretamente para a inicialização e autenticação normais.
  - **Exibição do fluxo de atualização**: ao rodar dentro da Store com update disponível, a `TelaDeAbertura` exibe o painel de atualização e interrompe a progressão automática.
- [x] 1.3 Criar os testes unitários em `editor/controllers/publish_controller_test.py` cobrindo:
  - **Bypass completo no Publish**: ao rodar fora da Store, a publicação não é bloqueada e segue o fluxo padrão de criação de PR.
  - **Bloqueio de publicação**: ao rodar dentro da Store com versão defasada, a publicação é bloqueada e exibe o diálogo para atualizar na Loja.
  - **Fallback aberto em erro**: falhas de conexão na checagem durante a publicação não bloqueiam o usuário.
- [x] 1.4 Assegurar 100% de cobertura de código (`unit test coverage`) em todas as novas rotinas e classes.

## 2. Implementação da Biblioteca `ServicoLoja` (Library-First)

- [x] 2.1 Implementar a classe `ServicoLoja` em `editor/core/servico_loja.py` (passando nos testes do TDD).
- [x] 2.2 Implementar a detecção segura de identidade de pacote MSIX e fallback gracioso (bypass transparente) para ambiente de desenvolvimento local, testes e CI.
- [x] 2.3 Implementar a consulta assíncrona na Microsoft Store via `StoreContext` (ou WinRT compatível).
- [x] 2.4 Implementar o método `solicitar_instalacao_atualizacao` com a estratégia híbrida: tentativa in-app via `RequestDownloadAndInstallStorePackageUpdatesAsync` e fallback resiliente abrindo `ms-windows-store://` e executando `QApplication.quit()`.

## 3. Integração no Boot (`TarefaInicializacao` & `TelaDeAbertura`)

- [x] 3.1 Integrar o `ServicoLoja` na `TarefaInicializacao` em `editor/core/worker.py`, pulando a checagem se não houver identidade MSIX.
- [x] 3.2 Implementar os sinais `atualizacao_disponivel` e `atualizacao_obrigatoria` na `TarefaInicializacao`.
- [x] 3.3 Adicionar componentes de UI na `TelaDeAbertura` para exibir aviso de nova versão disponível na Loja com botão "Atualizar na Microsoft Store".
- [x] 3.4 Conectar a ação do botão de atualização para chamar `solicitar_instalacao_atualizacao()` do `ServicoLoja`.

## 4. Guarda no Publish (`PublishController`)

- [x] 4.1 Modificar `iniciar_publicacao` no `PublishController` para consultar o `ServicoLoja` antes de prosseguir (pulando se fora da Store).
- [x] 4.2 Exibir diálogo informativo/crítico bloqueando a publicação se houver nova versão na Store, com botão acionando a atualização.
- [x] 4.3 Garantir fallback aberto em caso de falha de conexão na checagem da Loja durante a publicação.
