## 1. Fundação e Infraestrutura Base (TDD & Library-First)

- [ ] 1.1 Criar pacote `lib/auto_updater` com um arquivo `__init__.py` (vazio) para estabelecer a estrutura de biblioteca independente.
- [ ] 1.2 Criar `lib/auto_updater/config.py` e `lib/auto_updater/config_test.py` aplicando TDD para armazenar constantes do sistema (Paths de `%LOCALAPPDATA%`, nome de binário hardcoded, etc). Garantir 100% coverage.

## 2. Auto-Install e Lixeira Segura (TDD)

- [ ] 2.1 Criar `lib/auto_updater/installer_test.py` definindo os cenários (Red): Execução fora da pasta canônica (precisa copiar), dentro da canônica, falha de permissão.
- [ ] 2.2 Implementar `lib/auto_updater/installer.py` (Green e Refactor): Comparar paths, copiar via `shutil.copy2` para `%LOCALAPPDATA%\EditorAresta`, criar atalho `.lnk` de forma nativa e segura, salvar `cleanup_folder.txt`. Alcançar 100% de cobertura via mocks (os/shutil).
- [ ] 2.3 Criar `lib/auto_updater/cleaner_test.py` (Red): testar a leitura de `cleanup_folder.txt`, checagem de existência do binário obsoleto e matching estrito de `EditorAresta.old.exe`.
- [ ] 2.4 Implementar `lib/auto_updater/cleaner.py` (Green e Refactor) para remover especificamente e com segurança o lixo. 100% coverage.

## 3. Request Desacoplado de API (TDD)

- [ ] 3.1 Criar `lib/auto_updater/api_client_test.py` (Red): mockar `keyring` para testar cenários de requisição autenticada (token presente) e não-autenticada, mockar respostas da API do Github.
- [ ] 3.2 Implementar `lib/auto_updater/api_client.py` (Green e Refactor): usar o módulo `keyring` e extrair versão de release mais recente, ignorando módulos de interface gráfica (Qt).
- [ ] 3.3 Integrar o atualizador gráfico para notificar downloads no fluxo nativo, garantindo testes e cobertura.

## 4. O Rename Trick Final (TDD)

- [ ] 4.1 Criar `lib/auto_updater/rename_trick_test.py` (Red): testes que simulam o streaming de HTTP e a dança atômica do Windows de renomeação.
- [ ] 4.2 Implementar `lib/auto_updater/rename_trick.py` (Green e Refactor): Baixar binário como `EditorAresta.new`, orquestrar `os.rename(atual, atual + ".old.exe")`, renomear `.new` para o original, disparar `subprocess.Popen` e dar `sys.exit()`. 100% coverage.

## 5. Testes de Integração e Hook no Boot

- [ ] 5.1 Escrever teste de integração (`lib/auto_updater/integration_test.py`) testando o fluxo completo (Install -> Cleanup -> Check API -> Rename) sob ambiente controlado.
- [ ] 5.2 Em `main.py`, importar a nova biblioteca `lib.auto_updater` para injetar o fluxo de atualizações no prólogo da aplicação. Garantir que os testes de boot do app contemplem a injeção da biblioteca com 100% de cobertura.
