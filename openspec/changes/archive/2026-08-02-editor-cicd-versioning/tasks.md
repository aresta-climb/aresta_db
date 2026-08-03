## 1. Setup do Módulo de Versão (TDD & 100% Coverage)

- [x] 1.1 Criar o arquivo de teste `editor/core/version_test.py` cobrindo as validações da constante de versão (ex: tipagem e formato compatível com semver).
- [x] 1.2 Implementar `editor/core/version.py` com a constante `VERSION = "0.0.0-dev"` para fazer os testes passarem (Red, Green, Refactor).
- [x] 1.3 Adicionar testes garantindo a injeção/leitura da versão onde ela for consumida no sistema (ex: `editor/main_test.py` ou testes de UI).
- [x] 1.4 Importar e utilizar a constante `VERSION` no arquivo `editor/main.py`.
- [x] 1.5 Assegurar que os imports estão corretos para o PyInstaller capturar automaticamente o arquivo `version.py`.

## 2. Ferramenta de Bump de Versão (Library-First e TDD)

- [x] 2.1 Criar testes em `editor/release_tools/bump_version_test.py` cobrindo as rotinas de atualização da string de versão no arquivo `version.py` (cenários de sucesso, falha e validação de versão semver).
- [x] 2.2 Implementar o script `editor/release_tools/bump_version.py` fazendo os testes passarem e garantindo robustez na atualização das strings ao invés de usar `sed`.

## 3. GitHub Actions: Setup e Bumping

- [x] 3.1 Criar o arquivo de pipeline em `.github/workflows/release_editor.yml`.
- [x] 3.2 Configurar o gatilho `workflow_dispatch` com input para solicitar `new_version`.
- [x] 3.3 Implementar step de setup de Git Token (usando o `BOT_APP_ID` se aplicável).
- [x] 3.4 Invocar o script testado `editor/release_tools/bump_version.py` para injetar a nova versão solicitada.
- [x] 3.5 Realizar o commit "Lançar versão $FINAL_VERSION", criar a tag e efetuar o `git push`.

## 4. GitHub Actions: Testes e Build (PyInstaller)

- [x] 4.1 Adicionar o job de build rodando no runner `windows-latest`.
- [x] 4.2 Executar o setup do Python, instalar dependências e o PyInstaller.
- [x] 4.3 Rodar a suite de testes (`pytest`) como step obrigatório do pipeline antes de gerar o binário, quebrando o CI caso a cobertura não seja adequada ou existam falhas.
- [x] 4.4 Executar o comando do PyInstaller (ex: apontando para `editor/EditorAresta.spec`) gerando o binário `--onefile`.

## 5. GitHub Actions: Release e Ciclo -dev

- [x] 5.1 Fazer o upload do executável final via `softprops/action-gh-release` ou equivalente para a aba Releases.
- [x] 5.2 Concluída a Release, invocar o script `editor/release_tools/bump_version.py` para definir a versão como `<next-version>-dev`.
- [x] 5.3 Realizar commit com a mensagem "chore: iniciar ciclo de desenvolvimento" e disparar push para a `main`.
