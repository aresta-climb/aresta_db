## Context

O Aresta Editor é empacotado como aplicativo desktop Windows (MSIX) para distribuição na Microsoft Store (conforme configurado em `editor/msix/AppxManifest.xml`). A plataforma Windows fornece APIs WinRT dedicadas no namespace `Windows.Services.Store` (especificamente a classe `StoreContext`) e no namespace `Windows.ApplicationModel` para consultar o status do pacote e acionar a instalação de atualizações.

Para garantir que o código respeite os **Princípios de Engenharia Aresta (PRINCIPIOS.md)**:
1. **Tudo em Português** (código, comentários, variáveis, docs).
2. **Library-First**: As interações com a Loja e o sistema operacional devem residir em um serviço independente (`ServicoLoja`), desacoplado da interface gráfica (PyQt).
3. **100% de Unit Test Coverage**: Todas as rotinas serão testáveis de forma determinística via injeção de dependências e mocks de chamadas WinRT/OS.
4. **TDD**: Criação dos testes unitários e de integração antes do código de produção.

## Goals / Non-Goals

**Goals:**
- **[TDD & 100% Coverage]** Desenvolver a funcionalidade seguindo Red-Green-Refactor com 100% de cobertura nos testes unitários e de integração.
- **[Estratégia Híbrida de Update]** Priorizar a experiência integrada in-app via `RequestDownloadAndInstallStorePackageUpdatesAsync` e fornecer fallback automático via deep link `ms-windows-store://pdp/?ProductId=...` com encerramento gracioso.
- **[Bypass em Ambiente Não-Store]** Garantir que, se o app for executado fora da Microsoft Store (desenvolvimento local via `python main.py`, testes de CI, ou binário avulso), o sistema pule a checagem de versão de forma 100% transparente, sem emitir erros ou travar o fluxo do usuário.
- **[Library-First]** Criar o módulo `editor/core/servico_loja.py` encapsulando toda a lógica de WinRT/StoreContext e protocolo da Loja.
- **[Boot Check]** Integrar a checagem no fluxo de inicialização (`TarefaInicializacao` / `TelaDeAbertura`), apresentando a interface de atualização antes de abrir a tela de seleção de croquis quando rodando na Store com atualização disponível.
- **[Publish Guard]** Interceptar o `PublishController` para impedir publicações se a sessão local estiver defasada.

**Non-Goals:**
- Não reimplementar download manual de `.exe` ou mutações in-place via código próprio (a Microsoft Store e o Windows cuidam do download e substituição do pacote MSIX).
- Não criar daemons de background que fiquem consultando a loja continuamente em loop (as checagens ocorrem pontualmente no boot e no publish).

## Decisions

1. **Abordagem Library-First: `ServicoLoja` (`editor/core/servico_loja.py`)**
   - *Rationale*: A lógica de WinRT/Store e manipulação de protocolos do Windows deve ser autônoma e totalmente testável sem instanciar widgets Qt.
   - *Abordagem*: A classe `ServicoLoja` expõe métodos como:
     - `possui_identidade_pacote() -> bool`: Verifica se o processo está empacotado como MSIX.
     - `verificar_atualizacoes_disponiveis() -> ResultadoAtualizacao`: Consulta `StoreContext` de forma assíncrona ou retorna status seguro (`nao_aplicavel` quando fora da Store).
     - `solicitar_instalacao_atualizacao(parent_hwnd=None) -> bool`: Orquestra a tentativa in-app e fallback.
     - `abrir_pagina_na_loja(id_produto: str)`: Abre a página do produto na Loja via `QDesktopServices` e fecha o app.

2. **Estratégia Híbrida de Instalação (In-App + Deep Link Fallback)**
   - *Rationale*: Prover a melhor experiência nativa (modal in-app com barra de progresso do Windows) sem correr o risco de deixar o usuário travado se houver problemas com o serviço WinRT local.
   - *Abordagem*:
     - **Tentativa 1**: Executa `StoreContext.RequestDownloadAndInstallStorePackageUpdatesAsync`.
     - **Fallback (Tentativa 2)**: Se a chamada WinRT lançar exceção, retornar status de falha ou o módulo WinRT não estiver disponível:
       ```python
       QDesktopServices.openUrl(QUrl(f"ms-windows-store://pdp/?ProductId={ID_PRODUTO_STORE}"))
       QApplication.quit()
       ```
       O app da Loja assume o download e o editor se fecha para liberar locks de arquivo.

3. **Detecção e Bypass Transparente (Ambiente Não-Store)**
   - *Rationale*: Desenvolvedores e ambientes de CI rodam código fora do pacote MSIX (`APPMODEL_ERROR_NO_PACKAGE` / WinError 15700). O app não deve falhar nem exibir alertas espúrios.
   - *Abordagem*: `ServicoLoja.verificar_atualizacoes_disponiveis()` primeiro checa `possui_identidade_pacote()`. Se falso, retorna imediatamente um resultado neutro (`status = NAO_APLICAVEL`). A `TarefaInicializacao` e o `PublishController` identificam esse status e simplesmente continuam o fluxo sem interrupções.

4. **Integração na `TarefaInicializacao` e `TelaDeAbertura`**
   - *Rationale*: A checagem de versão logo no boot previne que o usuário gaste tempo editando arquivos em uma versão defasada.
   - *Abordagem*: A `TarefaInicializacao` executa a checagem logo após a verificação de pastas. Se houver atualização disponível (em ambiente Store), emite o sinal `atualizacao_disponivel(info)` para a `TelaDeAbertura`, que exibe uma seção com botão "Atualizar na Microsoft Store" e bloqueia a progressão automática. Caso contrário (ou fora da Store), prossegue normalmente.

5. **Guarda no `PublishController`**
   - *Rationale*: Se o editor ficar aberto durante dias e uma nova versão crítica for lançada, o envio de croquis deve ser protegido.
   - *Abordagem*: O método `iniciar_publicacao` faz uma checagem rápida chamando o `ServicoLoja`. Se constatar atualização, abre um diálogo instrutivo sugerindo atualizar o editor na Loja. Se estiver fora da Store ou em caso de erro de rede, concede bypass.

## Testing & TDD Strategy (Princípios de Engenharia Aresta)

- **100% de Cobertura Unitária**:
  - `editor/core/servico_loja_test.py`: Testa todos os caminhos do `ServicoLoja`:
    - **Cenário Não-Store**: Sem identidade de pacote MSIX -> bypass com retorno neutro.
    - **Cenário Store**: Com pacote MSIX mockado -> sem updates, com update opcional, com update obrigatório, erro de API/rede.
    - **Cenário In-App Sucesso**: Execução com sucesso de `RequestDownloadAndInstallStorePackageUpdatesAsync`.
    - **Cenário In-App Fallback**: Falha no WinRT acionando abertura de URL `ms-windows-store://` e `QApplication.quit()`.
  - `editor/views/tela_de_abertura_test.py` e `editor/core/worker_test.py`: Testa o boot pulando a checagem fora da Store e exibindo a interface quando houver update na Store.
  - `editor/controllers/publish_controller_test.py`: Testa o fluxo normal fora da Store e o bloqueio quando há atualização detectada na Store.
- **TDD (Red-Green-Refactor)**:
  - Os arquivos de teste `_test.py` serão criados com os cenários definidos antes da implementação de produção.
- **Mocks Herméticos**:
  - Mock de `winrt` / `StoreContext` e chamadas de sistema, garantindo execução rápida e determinística no `pytest`.
