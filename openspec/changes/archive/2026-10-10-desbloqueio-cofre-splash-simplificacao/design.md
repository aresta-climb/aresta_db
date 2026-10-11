# Design: Desbloqueio do Cofre na Splash Screen e Simplificação do PortalKeyring

## Context

Atualmente, o Aresta Editor invoca `configurar_cofre_credenciais()` e `cofre_disponivel()` de forma fragmentada e síncrona na thread principal durante a inicialização (`__init__`), impondo um timeout de 5 segundos na espera da resposta D-Bus do XDG Desktop Portal. Como demonstrado empiricamente, quando o cofre do sistema está trancado (comum em sessões com autologin), o GNOME Keyring apresenta o prompt nativo de senha na interface gráfica. No entanto, o timeout de 5 segundos aborta o socket D-Bus prematuramente antes da conclusão da digitação, gerando cancelamento de requisição no backend e deixando instâncias conflitantes do daemon em execução.

## Goals / Non-Goals

**Goals:**
- Exibir a `TelaDeAbertura` (Splash Screen) imediatamente no arranque do aplicativo, sem qualquer bloqueio de I/O de D-Bus ou cofre na thread principal (UI).
- Estabelecer uma etapa formal e dedicada na `TarefaInicializacao` (`QThread`) para o acesso ao cofre de credenciais, com atualização de progresso para 15%, emissão do status `"Acessando cofre de senhas do aplicativo..."` e pausa de 1.0s para leitura antes do disparo D-Bus.
- Eliminar o timeout de cliente na espera do sinal `Response` em `PortalKeyring` (`timeout=None`), garantindo que o diálogo de senha do sistema permaneça aberto até a decisão soberana do usuário (concluir com a senha ou cancelar com `Esc`/botão "Cancelar").
- Simplificar drasticamente o `PortalKeyring`, eliminando polling redundante e timeouts artificiais, mantendo apenas a leitura direta do pipe Unix e D-Bus via `jeepney`.
- Consolidar a inicialização do cofre em uma única invocação explícita (`GerenciadorSessao.inicializar_cofre() -> bool`), tornando o construtor `GerenciadorSessao()` livre de efeitos colaterais de I/O.
- Exibir aviso informativo de retenção temporária em memória RAM apenas caso o usuário opte por cancelar o diálogo nativo do sistema.

**Non-Goals:**
- Não alterar os contratos de plataformas como Windows (`WinVaultKeyring`) ou macOS (`Keychain`), que já operam com retorno booleano consistente.
- Não remover o suporte a fallback de sessão em memória RAM caso o cofre esteja indisponível ou cancelado.

## Decisions

### 1. Espera Sem Timeout (`timeout=None`) para o Sinal `Response` do Portal
- **Decisão**: Na invocação de `RetrieveSecret` do `PortalKeyring`, o método `recv_until_filtered` não utilizará timeout artificial de 5 segundos (`timeout=None`).
- **Racional**: Portais interativos do Freedesktop (`libportal`) delegam a temporização ao usuário e ao backend da interface gráfica. Se o usuário demorar para digitar a senha, o aplicativo deve aguardar pacientemente. Se o usuário clicar em "Cancelar" ou apertar `Esc`, o backend emite o sinal `Response` com código de erro imediatamente, destravando o cliente sem qualquer delay.
- **Alternativas consideradas**: Timeout de 60s ou 120s. Descartadas porque impõem encerramentos arbitrários caso o usuário demore mais tempo para buscar a senha, além de não acrescentarem benefício real, já que o cancelamento manual é instantâneo.

### 2. Desbloqueio como Etapa Formal da `TarefaInicializacao` (Worker Thread)
- **Decisão**: A `TarefaInicializacao` executará a etapa do cofre após a verificação de pastas locais (10%) e antes da verificação de sessão (25%). A thread emitirá `self.status.emit("Acessando cofre de senhas do aplicativo...")`, `self.progresso.emit(15)`, fará um `time.sleep(1.0)` para leitura clara e invocará `gerenciador_sessao.inicializar_cofre()`.
- **Racional**: Garante que o Aresta Editor já esteja visível na tela fornecendo contexto claro antes do prompt de senha do GNOME/KDE aparecer. Por rodar na `QThread`, a interface do usuário não congela.
- **Alternativas consideradas**: Invocar o cofre sob demanda apenas na hora de salvar o login. Descartada porque se o usuário já tiver uma sessão persistida no cofre, destrancá-lo logo na splash screen permite autenticar automaticamente sem sequer abrir a tela de login.

### 3. Construtor Puro e Inicialização Única no `GerenciadorSessao`
- **Decisão**: O construtor `GerenciadorSessao.__init__` deixa de chamar `configurar_cofre_credenciais()`. O método `inicializar_cofre() -> bool` é adicionado e chamado apenas pela `TarefaInicializacao`.
- **Racional**: Elimina chamadas redundantes repetidas por múltiplos consumidores e garante tempo previsível de instanciação em testes unitários e na UI.

### 4. Simplificação do `PortalKeyring`
- **Decisão**: Reduzir a complexidade de `PortalKeyring._call_retrieve_secret` e `_wait_pipe_readable`. O pipe Unix pode ser lido de forma direta (`os.read(read_fd, 1024)`) assim que o sinal `Response` com código 0 é recebido, já que o fechamento do `write_fd` pelo portal garante EOF ou dados prontos.

## Risks / Trade-offs

- **[Risco] Usuário abandona o diálogo de senha aberto**: Se o usuário deixar o prompt do sistema aberto e se afastar do computador, o Aresta permanecerá aguardando na splash screen.
  - *Mitigação*: A splash screen é executada com a UI viva e responsiva, permitindo que o usuário feche a aplicação no botão "×" a qualquer instante (`QApplication.quit()`).
- **[Risco] Cancelamento no diálogo nativo**: Se o usuário cancelar o diálogo de senha do sistema, ele precisará entender por que a sessão não será salva para a próxima vez.
  - *Mitigação*: A `TelaDeAbertura` exibe o banner amarelo com mensagem direta explicando que o cofre foi cancelado e que a sessão atual funcionará apenas em memória RAM.
