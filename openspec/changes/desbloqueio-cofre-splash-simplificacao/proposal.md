# Proposal: Desbloqueio do Cofre na Splash Screen e Simplificação do PortalKeyring

## Why

Atualmente, a verificação e o acesso ao cofre de credenciais do sistema operacional ocorrem de forma fragmentada, prematura e com timeout rígido de 5 segundos. Isso causa três problemas graves:
1. **Falta de Contexto ao Usuário**: Se o chaveiro do sistema estiver trancado (comum em setups com autologin), o diálogo de senha do sistema operacional é acionado antes mesmo da janela da aplicação ser renderizada na tela, assustando o usuário sem que ele compreenda qual aplicativo está solicitando acesso.
2. **Timeout Prematuro e Processos Zumbis**: Um timeout arbitrário de 5 segundos é insuficiente para a digitação de uma senha por um ser humano. Quando estoura, a conexão D-Bus é abortada prematuramente enquanto o prompt nativo ainda está aberto, cancelando a operação no backend e travando daemons como o `gnome-keyring` em loops de erro ("Backend call failed: The operation was cancelled").
3. **Múltiplas Tentativas Redundantes**: O cofre é consultado e reconfigurado repetidamente em vários pontos do ciclo de vida (no import, no construtor de `GerenciadorSessao`, na verificação de disponibilidade, no salvamento de credenciais e na tela de login).

Esta mudança organiza a inicialização do cofre como uma etapa formal e única na Splash Screen com tempo livre para resposta humana, e simplifica radicalmente a implementação do `PortalKeyring`.

## What Changes

- **Splash Screen First com Etapa Formal de Cofre**: A `TelaDeAbertura` é exibida imediatamente. A `TarefaInicializacao` (Worker thread) assume a responsabilidade de acessar o cofre como uma etapa formal de progresso, exibindo o status `"Acessando cofre de senhas do aplicativo..."` e aguardando 1.0 segundo para leitura antes de disparar o D-Bus.
- **Espera Sem Timeout de Cliente (`timeout=None`)**: A espera pelo sinal `Response` do `RetrieveSecret` deixa de impor um timeout curto de 5 segundos, aguardando a decisão soberana do usuário no diálogo do sistema (seja o preenchimento da senha ou o clique em "Cancelar" / tecla `Esc`).
- **Simplificação Radical do `PortalKeyring`**: Elimina códigos desnecessários de polling repetitivo, reconexões fragmentadas e probes artificiais. O backend foca na comunicação direta D-Bus via `jeepney` e leitura limpa do pipe Unix.
- **Inicialização Única (Once-and-Done)**: O cofre é inicializado exatamente uma vez pela `TarefaInicializacao`. O construtor `GerenciadorSessao()` deixa de executar I/O no `__init__`.
- **Aviso Consciente de Cancelamento**: Se o usuário explicitamente cancelar o diálogo do cofre nativo, o Aresta ativa o modo de sessão temporária em memória RAM e exibe o aviso na tela de login explicando com clareza a relação de causa e efeito.

## Capabilities

### Modified Capabilities
- `editor-inicializacao`: Adiciona a etapa formal de desbloqueio do cofre de senhas à `TarefaInicializacao` na splash screen, com mensagem visual e progresso dedicado antes da verificação de sessão.
- `keyring-portal-linux`: Simplifica o `PortalKeyring`, eliminando timeouts curtos arbitrários na espera da resposta do usuário (`timeout=None`) e simplificando o fluxo D-Bus de obtenção da chave mestra.
- `editor-autenticacao`: Padroniza a inicialização única do cofre, eliminando reconfigurações e probes redundantes, e condiciona a exibição do aviso de sessão temporária ao cancelamento explícito do cofre pelo usuário.

## Impact

- `editor/core/worker.py`: Inclusão da etapa de acesso ao cofre na thread de inicialização.
- `editor/core/gerenciador_sessao.py`: Remoção de chamadas síncronas de I/O no construtor e consolidação do estado do cofre.
- `editor/plataforma/linux/portal_keyring.py`: Simplificação do código D-Bus e remoção do timeout de 5 segundos.
- `editor/views/tela_de_abertura.py`: Recepção e apresentação harmoniosa do status de desbloqueio e controle do banner de aviso temporário.
- Cobertura de testes unitários: 100% de cobertura mantida em todos os módulos afetados.
