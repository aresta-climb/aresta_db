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
- **[Library-First]** Criar o módulo `editor/core/servico_loja.py` encapsulando toda a lógica de WinRT/StoreContext e protocolo da Loja.
- **[Boot Check]** Integrar a checagem no fluxo de inicialização (`TarefaInicializacao` / `TelaDeAbertura`), apresentando a interface de atualização antes de abrir a tela de seleção de croquis.
- **[Publish Guard]** Interceptar o `PublishController` para impedir publicações se a sessão local estiver defasada.
- **[Fallback em Dev]** Detectar se o aplicativo está rodando sem identidade de pacote MSIX (`APPMODEL_ERROR_NO_PACKAGE`), permitindo a execução transparente nos testes locais e de desenvolvimento.

**Non-Goals:**
- Não reimplementar download manual de `.exe` ou mutações in-place via código próprio (a Microsoft Store e o Windows cuidam do download e substituição do pacote MSIX).
- Não criar daemons de background que fiquem consultando a loja continuamente em loop (as checagens ocorrem pontualmente no boot e no publish).

## Decisions

1. **Abordagem Library-First: `ServicoLoja` (`editor/core/servico_loja.py`)**
   - *Rationale*: A lógica de WinRT/Store e manipulação de protocolos do Windows deve ser autônoma e totalmente testável sem instanciar widgets Qt.
   - *Abordagem*: A classe `ServicoLoja` expõe métodos como:
     - `possui_identidade_pacote() -> bool`: Verifica se o processo está empacotado como MSIX.
     - `verificar_atualizacoes_disponiveis() -> ResultadoAtualizacao`: Consulta `StoreContext` de forma assíncrona ou retorna status seguro.
     - `solicitar_instalacao_atualizacao(parent_hwnd=None) -> bool`: Dispara `RequestDownloadAndInstallStorePackageUpdatesAsync` da Store ou abre `ms-windows-store://pdp/?ProductId=...`.
     - `abrir_pagina_na_loja(id_produto: str)`: Abre a página do produto na Loja via `QDesktopServices` ou `os.startfile`.

2. **Integração na `TarefaInicializacao` e `TelaDeAbertura`**
   - *Rationale*: A checagem de versão logo no boot previne que o usuário gaste tempo editando arquivos em uma versão defasada.
   - *Abordagem*: A `TarefaInicializacao` executa a checagem logo após a verificação de pastas. Se houver atualização obrigatória ou disponível, emite o sinal `atualizacao_disponivel(info)` para a `TelaDeAbertura`, que exibe uma seção/diálogo com botão "Atualizar na Microsoft Store" e bloqueia a progressão automática.

3. **Guarda no `PublishController`**
   - *Rationale*: Se o editor ficar aberto durante dias e uma nova versão crítica for lançada, o envio de croquis deve ser protegido.
   - *Abordagem*: O método `iniciar_publicacao` faz uma checagem rápida chamando o `ServicoLoja`. Se constatar atualização, abre um diálogo instrutivo sugerindo reiniciar e atualizar o editor na Loja.

4. **Tratamento de Falhas e Fallback em Ambiente de Desenvolvimento**
   - *Rationale*: Durante desenvolvimento (`python editor/main.py`) e na esteira de CI (pytest), o processo roda fora do contêiner MSIX.
   - *Abordagem*: O `ServicoLoja` intercepta exceções do tipo `ImportError` (se o módulo winrt não estiver presente) ou `OSError / WinError 15700` (sem identidade de pacote) e retorna que nenhuma atualização é necessária, garantindo funcionamento suave em dev.

## Testing & TDD Strategy (Princípios de Engenharia Aresta)

- **100% de Cobertura Unitária**:
  - `editor/core/servico_loja_test.py`: Testa todos os caminhos do `ServicoLoja` (com pacote MSIX mockado, sem pacote, updates disponíveis, falhas de rede, chamadas de instalação).
  - `editor/views/tela_de_abertura_test.py`: Testa a renderização da interface quando o sinal de atualização é emitido.
  - `editor/controllers/publish_controller_test.py`: Testa o bloqueio de publicação quando há atualização detectada.
- **TDD (Red-Green-Refactor)**:
  - Os arquivos de teste `_test.py` serão criados com os cenários definidos antes da implementação de produção.
- **Mocks Herméticos**:
  - Mock de `winrt` / `StoreContext` e chamadas de sistema, garantindo execução rápida e determinística no `pytest`.
