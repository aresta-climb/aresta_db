# Proposal

## Why

Atualmente, o Editor Aresta no Linux solicita permissões D-Bus irrestritas no manifesto Flatpak (`--talk-name=org.freedesktop.secrets` e `--talk-name=org.kde.kwalletd*`) para permitir que a biblioteca Python `keyring` armazene o token de autenticação do usuário. Essa abordagem viola as diretrizes de confinamento e segurança do Flathub, pois o protocolo legado do Secret Service expõe todas as senhas armazenadas no chaveiro do sistema operacional sem isolamento por aplicativo.

Além disso, a biblioteca padrão `keyring` não possui backend nativo para o portal seguro do FreeDesktop (`org.freedesktop.portal.Secret`). Esta proposta implementa uma biblioteca independente de backend do `keyring` baseada em `jeepney` e criptografia simétrica AES-256-GCM, escrita em inglês para viabilizar sua posterior contribuição ao projeto upstream (`jaraco/keyring`), fechando as brechas de segurança no Flatpak e mantendo o fallback transparente fora da sandbox.

## What Changes

- **Adição da biblioteca `jeepney`**: inclusão do cliente puro Python para protocolo D-Bus com suporte nativo a descritores de arquivo Unix (FD negotiation).
- **Novo Backend `PortalKeyring` (`editor/plataforma/linux/portal_keyring.py`)**: implementação de `keyring.backend.KeyringBackend` compatível com `org.freedesktop.portal.Secret` via `RetrieveSecret`, armazenando segredos em arquivo local cifrado com AES-256-GCM e chave mestre isolada por App ID.
- **Exceção de Nomenclatura em Inglês**: o módulo `portal_keyring.py` e sua suíte de testes `portal_keyring_test.py` são redigidos integralmente em inglês, visando facilitar a doação do código como contribuição upstream ou pacote PyPI independente (`keyring-portal`).
- **Encadeamento de Fallback no `AdaptadorLinux`**: `AdaptadorLinux.configurar_cofre_credenciais` tenta registrar o `PortalKeyring` prioritariamente quando em ambiente Flatpak ou quando o portal responder; caso contrário, efetua fallback automático para `SecretService`, `kwallet` ou cofre neutro em memória.
- **Sanitização de Permissões Flatpak**: remoção das permissões de D-Bus `--talk-name=org.freedesktop.secrets`, `--talk-name=org.kde.kwalletd5` e `--talk-name=org.kde.kwalletd` do manifesto `com.arestaclimb.Editor.yaml` (tanto em `aresta_db` quanto em `aresta-editor-flathub`).

## Capabilities

### New Capabilities
- `keyring-portal-linux`: Implementação de backend para a biblioteca `keyring` do Python que utiliza o `org.freedesktop.portal.Secret` e criptografia local AES-256-GCM para armazenamento seguro de credenciais em ambientes confinados Linux.

### Modified Capabilities
- `editor-distribuicao-linux`: Atualização do requisito de integração com Portals e permissões da sandbox para proibir o acesso irrestrito ao Secret Service legado e exigir o uso estrito do Portal Secret.

## Impact

- **Código Afetado**: `editor/plataforma/linux/portal_keyring.py` (novo), `editor/plataforma/linux/integracao.py`, `editor/flatpak/com.arestaclimb.Editor.yaml`, `.github/workflows/build_editor_linux.yml`.
- **Dependências**: Adição de `jeepney` às dependências de produção do grupo `editor` em `pyproject.toml` e `uv.lock`.
- **APIs e Contratos**: Nenhuma quebra de contrato no `editor/core/gerenciador_sessao.py`, pois a interface consumida continua sendo a API pública e agnóstica de `keyring.get_password` e `keyring.set_password`.
- **Segurança da Sandbox**: Redução drástica da superfície de ataque do pacote Flatpak, atendendo com rigor aos requisitos dos revisores do Flathub.
