# Design

## Context

Conforme estabelecido em `proposal.md`, o empacotamento Flatpak do Editor Aresta atualmente requisita permissões de D-Bus para o Secret Service legado (`org.freedesktop.secrets` e `org.kde.kwalletd*`). A sandbox do Flatpak restringe o acesso direto ao barramento do sistema, mas expõe por padrão o barramento de portais `org.freedesktop.portal.Desktop`.

A interface `org.freedesktop.portal.Secret` disponibiliza o método `RetrieveSecret(h: fd, options: dict) -> handle: path`, projetado para entregar uma chave mestre opaca exclusiva para o App ID e usuário. Como a biblioteca oficial Python `keyring` ainda não possui suporte nativo a este portal (Issue #748 no repositório `jaraco/keyring`), este design detalha a arquitetura de um backend desacoplado, escrito em inglês, pronto para uso imediato no Editor Aresta e posterior contribuição upstream.

## Goals / Non-Goals

**Goals:**
- Implementar `PortalKeyring(KeyringBackend)` utilizando `jeepney` com transferência de descritores de arquivo Unix (`enable_fds=True`).
- Gerenciar armazenamento local de segredos em `$XDG_DATA_HOME/keyring.enc` cifrado com AES-256-GCM através da chave mestre obtida do portal.
- Definir `priority = 5.0` dinamicamente quando o portal responder com sucesso, e `0.0` caso contrário.
- Escrever `portal_keyring.py` e `portal_keyring_test.py` 100% em inglês, agnósticos a qualquer dependência interna do Aresta.
- Integrar a seleção prioritária do backend no `AdaptadorLinux.configurar_cofre_credenciais` com fallback seguro para ambientes fora da sandbox.
- Eliminar as diretivas `--talk-name=org.freedesktop.secrets` e `--talk-name=org.kde.kwalletd*` do manifesto Flatpak.

**Non-Goals:**
- Submeter o PR para o repositório `jaraco/keyring` nesta etapa (o envio upstream ocorrerá após validação em produção).
- Modificar o armazenamento de credenciais no Windows (WinVault) ou macOS (Keychain).
- Alterar o contrato de `editor/core/gerenciador_sessao.py`.

## Decisions

### Decisão 1: Utilização de `jeepney` para comunicação D-Bus
- **Decisão**: Conectar ao barramento de sessão via `jeepney.io.blocking.open_dbus_connection(bus='SESSION', enable_fds=True)` e invocar o método `RetrieveSecret`.
- **Racional**: `jeepney` é uma biblioteca pura Python, sem extensões compiladas em C, e já é a dependência padrão adotada pelo `secretstorage` (usado pelo próprio `keyring` no Linux). Seu suporte a `enable_fds=True` permite enviar pipes Unix nativamente.
- **Alternativas consideradas**:
  - `PySide6.QtDBus`: Acoplaria a biblioteca ao Qt/GUI, inviabilizando sua doação como backend genérico do `keyring` no upstream.
  - `dbus-python`: Requer cabeçalhos C de desenvolvimento do `libdbus-1-dev`, violando a portabilidade e aumentando o tamanho do empacotamento.

### Decisão 2: Armazenamento local cifrado com AES-256-GCM
- **Decisão**: A chave mestre recebida pelo portal (expandida/normalizada para 32 bytes) é usada para cifrar um dicionário serializado em JSON com AES-256-GCM e nonce aleatório de 96 bits gravado de forma atômica (arquivo temporário seguido de `replace`).
- **Racional**: O portal do FreeDesktop não armazena múltiplos pares serviço/usuário/senha; ele fornece uma semente criptográfica estável por aplicativo. O envelope local AES-GCM garante confidencialidade e integridade criptográfica contra adulteração.
- **Alternativas consideradas**:
  - `SQLCipher`: Adicionaria dependência pesada de biblioteca nativa C.
  - Arquivo em texto puro: Violaria a segurança básica de armazenamento de senhas.

### Decisão 3: Redação do backend e testes em Inglês
- **Decisão**: `editor/plataforma/linux/portal_keyring.py` e seu teste `portal_keyring_test.py` serão redigidos estritamente em inglês.
- **Racional**: O código será publicado no PyPI ou submetido como Pull Request no repositório `jaraco/keyring`. Manter a biblioteca em inglês desde a concepção elimina trabalho duplicado de tradução e refatoração posterior.
- **Alternativas consideradas**:
  - Código em português: Dificultaria a colaboração com a comunidade internacional do `keyring`.

### Decisão 4: Fallback transparente no `AdaptadorLinux`
- **Decisão**: No `AdaptadorLinux.configurar_cofre_credenciais()`, verificar a disponibilidade do `PortalKeyring`. Se indisponível (ex: execução fora do Flatpak ou ambiente de desenvolvimento sem o daemon do portal rodando), tentar `SecretService` e `kwallet`.
- **Racional**: Permite que desenvolvedores continuem rodando `python -m editor.main` no host local ou testes sem necessidade de emular a sandbox do Flatpak.

## Risks / Trade-offs

- **[Risco] Incompatibilidade com plataformas não-POSIX (ex: Windows dev)** → *Mitigação*: Importações de `jeepney` e manipulações de descritores de arquivo Unix são encapsuladas e isoladas com guardas de plataforma, permitindo que a suíte de testes unitários execute com mocks no Windows e no Linux.
- **[Risco] Corrupção de arquivo de credenciais em encerramento abrupto** → *Mitigação*: A gravação do cofre local usa escrita atômica via arquivo temporário no mesmo sistema de arquivos (`tempfile.NamedTemporaryFile` + `os.replace`).
- **[Risco] Bloqueio ou lentidão na chamada D-Bus** → *Mitigação*: A chave mestre do portal é requisitada apenas na primeira operação de leitura/escrita e mantida em cache de memória pelo tempo de vida do processo.
