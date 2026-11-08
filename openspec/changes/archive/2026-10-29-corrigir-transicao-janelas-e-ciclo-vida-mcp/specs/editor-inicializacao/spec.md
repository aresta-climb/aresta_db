# Spec Delta

## MODIFIED Requirements

### Requirement: Fluxo de Transição para Janela Principal

A aplicação MUST preservar o loop principal de eventos (`app.exec()`) ativo durante todas as transições entre a `TelaDeAbertura`, a `TelaDeCarregamento` e a `JanelaPrincipal`, fechando a janela anterior e exibindo a próxima sem disparar o encerramento automático do aplicativo por ausência temporária de janelas visíveis. O processo só MUST encerrar quando o usuário cancelar explicitamente a `TelaDeCarregamento` (sem logout em andamento) ou fechar todas as janelas principais abertas.

#### Scenario: Inicialização Concluída
- **WHEN** todas as etapas de inicialização (pastas, autenticação, sincronização) forem concluídas com sucesso
- **THEN** a `TelaDeAbertura` MUST ser fechada e a `TelaDeCarregamento` MUST ser exibida mantendo o loop principal de eventos ativo

#### Scenario: Abertura de Croqui Oficial, Novo ou Existente a partir da Tela de Carregamento
- **WHEN** o usuário (ou agente via MCP) cria um novo croqui, importa um croqui oficial ou seleciona um croqui do histórico na `TelaDeCarregamento` e o diálogo é aceito
- **THEN** a `JanelaPrincipal` MUST ser instanciada com o croqui selecionado, exibida na tela e mantida viva no loop principal de eventos (`app.exec()`), sem que o fechamento intermediário da `TelaDeCarregamento` dispare `aboutToQuit` ou encerre a aplicação

#### Scenario: Retorno da Janela Principal para a Tela de Carregamento via Abrir Novo
- **WHEN** o usuário aciona a opção "Abrir Novo" na `JanelaPrincipal` para selecionar outro croqui
- **THEN** a `JanelaPrincipal` anterior MUST ser fechada e a `TelaDeCarregamento` MUST ser reaberta sem encerrar o loop principal de eventos da aplicação
