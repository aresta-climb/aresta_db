# Tasks

## 1. Dependências do Projeto

- [x] 1.1 Adicionar `jeepney` ao grupo de dependências `editor` no `pyproject.toml` e atualizar `uv.lock` via `uv lock`, verificando que a biblioteca é instalada com sucesso.

## 2. Implementação do PortalKeyring (TDD em Inglês)

- [x] 2.1 Criar a suíte de testes unitários `editor/plataforma/linux/portal_keyring_test.py` em inglês cobrindo: comunicação D-Bus `RetrieveSecret` com passagem de Unix FD (mockando Jeepney), extração de chave mestre, criptografia e decriptografia AES-256-GCM no cofre local, persistência atômica, exclusão de senhas e cálculo de `priority`.
- [x] 2.2 Implementar a biblioteca `editor/plataforma/linux/portal_keyring.py` em inglês herdando de `keyring.backend.KeyringBackend`, provendo a classe `PortalKeyring` (com alias `Keyring = PortalKeyring`) e verificando que 100% dos testes de `portal_keyring_test.py` passam.

## 3. Integração com AdaptadorLinux e Fallback

- [x] 3.1 Atualizar `editor/plataforma/linux/integracao_test.py` com cenários de teste validando o registro preferencial de `PortalKeyring` quando o portal estiver funcional e o encadeamento de fallback transparente para `SecretService`, `kwallet` ou neutral fallback.
- [x] 3.2 Atualizar o método `configurar_cofre_credenciais` em `editor/plataforma/linux/integracao.py` para instanciar e registrar o `PortalKeyring` prioritariamente quando em Flatpak ou com portal ativo, verificando que os testes passam.

## 4. Sanitização do Manifesto Flatpak e Validação

- [x] 4.1 Remover `--talk-name=org.freedesktop.secrets`, `--talk-name=org.kde.kwalletd5` e `--talk-name=org.kde.kwalletd` do manifesto `editor/flatpak/com.arestaclimb.Editor.yaml` e atualizar asserções em `editor/build_test.py`, verificando conformidade estrita da sandbox.
- [x] 4.2 Executar a suíte completa de testes do `editor/` via `uv run pytest` para garantir 100% de cobertura e aprovação geral.
