## 1. Testes de Integração e TDD Inicial (Princípios III, IV e V)

- [ ] 1.1 Criar a suíte de testes unitários `editor/core/servico_loja_test.py` cobrindo:
  - Detecção de identidade de pacote MSIX (presente vs ausente em ambiente dev).
  - Consulta de atualizações na Microsoft Store com mock de `StoreContext` (sem updates, update opcional, update obrigatório, falha de rede/API).
  - Ação de solicitar atualização nativa e abertura de protocolo `ms-windows-store://`.
- [ ] 1.2 Criar os testes unitários em `editor/views/tela_de_abertura_test.py` cobrindo a interface visual de notificação de atualização da Store.
- [ ] 1.3 Criar os testes unitários em `editor/controllers/publish_controller_test.py` cobrindo o bloqueio da publicação quando detectada versão defasada na Store.
- [ ] 1.4 Assegurar 100% de cobertura de código (`unit test coverage`) em todas as novas rotinas e classes.

## 2. Implementação da Biblioteca `ServicoLoja` (Library-First)

- [ ] 2.1 Implementar a classe `ServicoLoja` em `editor/core/servico_loja.py` (passando nos testes do TDD).
- [ ] 2.2 Implementar a detecção segura de identidade de pacote MSIX e fallback gracioso para ambiente de desenvolvimento local e CI.
- [ ] 2.3 Implementar a consulta assíncrona na Microsoft Store via `StoreContext` (ou WinRT compatível).
- [ ] 2.4 Implementar os métodos de acionamento da UI nativa de instalação de update da Store e abertura do protocolo `ms-windows-store://`.

## 3. Integração no Boot (`TarefaInicializacao` & `TelaDeAbertura`)

- [ ] 3.1 Integrar o `ServicoLoja` na `TarefaInicializacao` em `editor/core/worker.py`, adicionando o passo de verificação da Microsoft Store.
- [ ] 3.2 Implementar os sinais `atualizacao_disponivel` e `atualizacao_obrigatoria` na `TarefaInicializacao`.
- [ ] 3.3 Adicionar componentes de UI na `TelaDeAbertura` para exibir aviso de nova versão disponível na Loja com botão "Atualizar na Microsoft Store".
- [ ] 3.4 Conectar a ação do botão de atualização para disparar o instalador da Store / protocolo e fechar o aplicativo para a atualização do pacote MSIX.

## 4. Guarda no Publish (`PublishController`)

- [ ] 4.1 Modificar `iniciar_publicacao` no `PublishController` para consultar o `ServicoLoja` antes de prosseguir.
- [ ] 4.2 Exibir diálogo informativo/crítico bloqueando a publicação se houver nova versão na Store, com botão de abrir a Microsoft Store.
- [ ] 4.3 Garantir fallback aberto em caso de falha de conexão na checagem da Loja durante a publicação.
