## Why

Com a migração da distribuição e empacotamento do Aresta Editor para o formato MSIX via **Microsoft Store**, a integridade dos dados e o ciclo de vida do aplicativo passam a ser gerenciados pela infraestrutura da plataforma Windows. 

No entanto, usuários podem iniciar o editor com versões desatualizadas ou manter sessões abertas por dias enquanto uma nova versão do aplicativo com alterações no esquema de dados (Protobuf / YAML) é publicada na loja. Para evitar corrupção ou inconsistência no banco de dados comunitário, o editor deve checar ativamente na **Microsoft Store** se há atualizações disponíveis:
1. **No Boot (Tela de Abertura)**: Antes de abrir a seleção de croquis ou área principal, o app verifica a disponibilidade de novas versões na Loja. Se houver atualização (especialmente obrigatória), exibe a interface de atualização nativa ou direciona para a Microsoft Store.
2. **Na Publicação (Guarda no Publish)**: Como salvaguarda para sessões de longa duração, uma checagem rápida impede o envio de dados caso o editor tenha ficado desatualizado durante a sessão.

Seguindo o **PRINCIPIOS.md**, toda a lógica será desenvolvida com **TDD**, **100% de cobertura de testes unitários**, abordagem **Library-First** e código 100% em **Português**.

## What Changes

- **Biblioteca `ServicoLoja` (Library-First)**: Criação de um módulo isolado (`editor/core/servico_loja.py`) responsável por interagir com as APIs da Microsoft Store (`Windows.Services.Store.StoreContext` via WinRT), detectar se a aplicação roda empacotada com identidade MSIX (*Package Identity*), checar updates de forma assíncrona e orquestrar a instalação.
- **Estratégia Híbrida de Atualização**:
  - **Via Principal (In-App)**: Executa `RequestDownloadAndInstallStorePackageUpdatesAsync` da API WinRT, apresentando a janela modal oficial do Windows com a barra de download sobreposta ao app.
  - **Fallback Seguro (Deep Link)**: Caso a chamada WinRT falhe ou não esteja disponível, aciona o protocolo `ms-windows-store://pdp/?ProductId=...` e comanda o encerramento gracioso da aplicação (`QApplication.quit()`), garantindo que o usuário nunca fique bloqueado sem conseguir atualizar.
- **Checagem de Atualização na Inicialização (`TelaDeAbertura` / `TarefaInicializacao`)**:
  - Durante o boot, uma etapa "Verificando atualizações na Microsoft Store..." é executada.
  - Em ambiente de desenvolvimento local (sem identidade MSIX), a checagem é ignorada graciosamente (fallback aberto / bypass transparente).
  - Em ambiente de produção (MSIX), havendo atualização disponível/obrigatória, a `TelaDeAbertura` exibe aviso e botão para disparar o update na Store antes de liberar o editor.
- **Guarda no `PublishController`**:
  - Antes de iniciar a publicação, verifica se o editor está defasado em relação à Loja. Se estiver, interrompe o fluxo e solicita que o usuário atualize o app.
- **TDD Rigoroso e Mocks**:
  - Todos os cenários (presença de identidade MSIX, ausência de pacote/dev, update obrigatório, update opcional, erro de rede, sucesso do in-app update, fallback para deep link) serão cobertos por testes unitários com mocks completos, garantindo 100% de cobertura no CI.

## Capabilities

### New Capabilities
- `store-update-guard`: Verificação de versões e orquestração de atualizações via APIs da Microsoft Store (WinRT `StoreContext` e URI `ms-windows-store://`), tanto no boot quanto na publicação.

### Modified Capabilities
- `editor-inicializacao`: Adiciona a etapa de checagem da Microsoft Store na `TarefaInicializacao` e interface na `TelaDeAbertura`.
- `publicacao-croqui`: Adiciona validação de versão da loja no `PublishController`.

## Impact

- Inicialização segura: impede que usuários iniciem trabalhos ou editem croquis em versões defasadas.
- Experiência nativa do Windows: diálogo integrado com barra de progresso nativa do Windows Store, com fallback 100% resiliente para o app da Loja.
- Zero impacto no ambiente de desenvolvimento: desenvolvedores rodando via Python local continuam com fluxo normal sem bloqueios.
