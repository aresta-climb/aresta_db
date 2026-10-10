# Tasks

## 1. Simplificação e Resiliência do PortalKeyring

- [x] 1.1 Atualizar testes unitários em `editor/plataforma/linux/portal_keyring_test.py` cobrindo cenários de timeout, cancelamento pelo portal (`response_code != 0`), e leitura com polling no descritor de arquivo Unix
- [x] 1.2 Simplificar `editor/plataforma/linux/portal_keyring.py` utilizando `select.poll()` e timeouts rigorosos para leitura do segredo mestre, tratando erros com `KeyringError`, e verificar aprovação de 100% dos testes de unidade com cobertura total

## 2. Verificação de Disponibilidade do Cofre no GerenciadorSessao

- [x] 2.1 Adicionar testes unitários em `editor/core/gerenciador_sessao_test.py` para o método `cofre_disponivel()` e para o fallback de retenção de sessão em memória RAM quando o cofre estiver trancado/inacessível
- [x] 2.2 Implementar o método `cofre_disponivel()` e o fallback resiliente em `editor/core/gerenciador_sessao.py`, e verificar aprovação com 100% de cobertura de testes

## 3. Banner Informativo na Tela de Abertura (SplashScreen)

- [x] 3.1 Criar testes unitários em `editor/views/tela_de_abertura_test.py` para verificar a renderização e o controle de visibilidade do banner de aviso de cofre trancado na tela de login
- [x] 3.2 Implementar o banner `label_aviso_cofre` em `editor/views/tela_de_abertura.py` com o texto exato *"Cofre do sistema está trancado; para que sua sessão seja lembrada na próxima vez que abrir o app, desbloqueie o cofre de senhas do sistema."*, exibindo-o quando `cofre_disponivel()` for falso, e verificar aprovação com 100% de cobertura de testes

## 4. Conformidade Flathub e Validação Final

- [x] 4.1 Atualizar o manifesto Flatpak `editor/flatpak/com.arestaclimb.Editor.yaml` removendo permissões obsoletas de D-Bus (`--talk-name=org.kde.kwalletd` e `--talk-name=org.kde.kwalletd5`)
- [x] 4.2 Executar a suíte de testes completa do repositório (`pytest`) e validar integridade geral
