# Design

## Context

No Linux Flatpak, o aplicativo utiliza o `PortalKeyring` (`org.freedesktop.portal.Secret`) para persistir chaves de sessão de forma criptografada e isolada. Quando o chaveiro do sistema (GNOME Keyring / KWallet) está trancado — comum em instalações com login automático (*auto-login*) —, o portal não abre prompt interativo e cancela a operação. Se o código cliente esperar indefinidamente no pipe Unix ou se a aplicação tentar acessar chaves sem tratamento de erro, a interface gráfica pode travar ou apresentar falha silenciosa. Além disso, o Flathub não autoriza permissões amplas (`--talk-name=org.freedesktop.secrets`).

Para mais detalhes da motivação, consulte [proposal.md](proposal.md) e os deltas em [specs/](specs/).

## Goals / Non-Goals

**Goals:**
- **Simplificação e Não-Bloqueio**: Tornar a implementação do `PortalKeyring` direta e resiliente usando `jeepney` e `select.poll()` com timeout explícito, levantando `KeyringError` imediatamente em caso de erro/cancelamento.
- **Detecção Precoce do Cofre**: Fornecer método `GerenciadorSessao.cofre_disponivel()` que testa se o chaveiro do sistema está funcional e destrancado.
- **Aviso Informativo na Splashscreen**: Exibir banner de alerta na `TelaDeAbertura` antes que o usuário inicie o login:
  *"Cofre do sistema está trancado; para que sua sessão seja lembrada na próxima vez que abrir o app, desbloqueie o cofre de senhas do sistema."*
- **Sessão em Memória Resiliente**: Permitir que o login prossiga normalmente armazenando tokens em memória quando o cofre estiver trancado.
- **Conformidade de Sandbox**: Limpar permissões obsoletas de D-Bus (`org.kde.kwalletd`, `org.kde.kwalletd5`) do manifesto Flatpak.
- **100% Cobertura de Testes Unitários**: Garantir cobertura completa em conformidade com as regras do projeto.

**Non-Goals:**
- Solicitar permissões irrestritas de host (`--talk-name=org.freedesktop.secrets`).
- Exibir caixas de diálogo modais bloqueantes pós-login.
- Implementar suporte a TPM 2.0 direto via sandbox.

## Decisions

### Decisão 1: Simplificação do `PortalKeyring` com `select.poll` e timeout curto
- **Abordagem**: Em `PortalKeyring._recuperar_segredo_mestre()`, o pipe Unix é lido apenas após confirmação de prontidão via `select.poll()` com timeout de 3.000 ms. Se o retorno do portal indicar cancelamento (`response_code != 0`), levanta `KeyringError` imediatamente.
- **Alternativas consideradas**:
  - Leitura síncrona direta com `os.read()`: Descartada pois causaria travamento na thread caso o descritor de arquivo permanecesse aberto sem escrita.
  - Laço de polling com `time.sleep`: Descartada por ser menos eficiente e não idiomática para I/O em Unix.

### Decisão 2: Método `cofre_disponivel()` em `GerenciadorSessao`
- **Abordagem**: `GerenciadorSessao.cofre_disponivel() -> bool` executa uma chamada de sonda protegida (`keyring.get_password("aresta-climb", "__teste_cofre__")`). Caso retorne sem exceções (ou com `None`), o cofre está disponível. Se disparar `KeyringError`, `RuntimeError` ou erro de D-Bus, captura a exceção e retorna `False`.
- **Alternativas consideradas**:
  - Consulta direta a interfaces D-Bus externas: Descartada pois violaria a abstração de multiplataforma (Windows/macOS/Linux) e exigiria permissões restritas.

### Decisão 3: Banner inline estático na `TelaDeAbertura`
- **Abordagem**: Um widget `QLabel` informativo (`label_aviso_cofre`) é posicionado na tela de autenticação da `TelaDeAbertura`, acima dos campos de entrada de e-mail. Caso `cofre_disponivel()` retorne `False` no momento de exibir a tela de login, o banner torna-se visível com o texto definido.
- **Alternativas consideradas**:
  - `QMessageBox` modal pós-login: Descartada por interromper o fluxo do usuário tardiamente.

### Decisão 4: Fallback de persistência em memória
- **Abordagem**: Em caso de falha de escrita no chaveiro (`KeyringError`), `GerenciadorSessao.salvar_sessao()` retém os tokens e dados de usuário no atributo `_sessao_memoria` e loga um aviso, permitindo a continuidade do fluxo sem exceção fatal.

## Risks / Trade-offs

- **[Chaveiro trancado em distros com auto-login]** → *Mitigação*: O banner orienta o usuário precocemente, e o app mantém a sessão ativa em memória RAM durante o uso.
- **[Atraso de inicialização na verificação de cofre em máquinas lentas]** → *Mitigação*: Timeout de sonda enxuto (máximo 3s) e caching da chave mestre em memória após a primeira leitura bem-sucedida.
