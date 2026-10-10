# Proposal

## Why

No Linux Flatpak, o acesso a credenciais seguras através do XDG Desktop Portal Secret (`org.freedesktop.portal.Secret`) falha de forma silenciosa ou bloqueante quando o cofre de senhas do sistema operacional (GNOME Keyring / KWallet) está bloqueado (cenário típico de distribuições ou VMs configuradas com *auto-login*). Como o portal é estritamente não-interativo e a sandbox bloqueia chamadas diretas de desbloqueio ao `org.freedesktop.secrets`, o aplicativo precisa:
1. Simplificar e proteger a comunicação D-Bus/pipe contra travamentos por meio de timeouts explícitos e tratamento de erro sem bloqueios.
2. Alertar visualmente o usuário na tela de abertura (*splashscreen*) antes do login de que o cofre está trancado, permitindo que ele tome uma ação corretiva ou prossiga sabendo que a sessão ficará retida apenas em memória enquanto o aplicativo estiver aberto.

## What Changes

- **Simplificação e resiliência no `PortalKeyring`**:
  - Elimina leituras bloqueantes no pipe D-Bus, utilizando verificação com `select.poll()` e timeouts rigorosos.
  - Simplifica o despacho D-Bus jeepney para aguardar o sinal `Response` da requisição sem fechar prematuramente a conexão.
  - Trata respostas de erro (código `!= 0`) ou cancelamento levantando `KeyringError` imediato sem travar a interface.
- **Detecção precoce e aviso visual na Splash Screen (`TelaDeAbertura`)**:
  - Adiciona método de verificação de disponibilidade do cofre em `GerenciadorSessao.cofre_disponivel()`.
  - Exibe banner de aviso na tela de autenticação da tela de abertura: *"Cofre do sistema está trancado; para que sua sessão seja lembrada na próxima vez que abrir o app, desbloqueie o cofre de senhas do sistema."* caso o cofre esteja inacessível/bloqueado.
- **Conformidade estrita com o Flathub**:
  - Mantém o manifesto Flatpak sem as permissões irrestritas `--talk-name=org.freedesktop.secrets`, `--talk-name=org.kde.kwalletd` e `--talk-name=org.kde.kwalletd5`.

## Capabilities

### Modified Capabilities
- `keyring-portal-linux`: Atualiza requisitos de resiliência, timeouts e simplificação da comunicação D-Bus com `org.freedesktop.portal.Secret`.
- `editor-autenticacao`: Adiciona requisito de detecção precoce de cofre bloqueado e exibição de aviso informativo na tela de autenticação, além de fallback gracioso para memória.

## Impact

- Código afetado:
  - `editor/plataforma/linux/portal_keyring.py`
  - `editor/plataforma/linux/portal_keyring_test.py`
  - `editor/core/gerenciador_sessao.py`
  - `editor/core/gerenciador_sessao_test.py`
  - `editor/views/tela_de_abertura.py`
  - `editor/views/tela_de_abertura_test.py`
  - `editor/main.py`
  - `editor/main_test.py`
  - `editor/flatpak/com.arestaclimb.Editor.yaml`
- APIs/Dependências:
  - Nenhuma dependência externa adicionada. Utiliza `jeepney` e `select` padrão.
