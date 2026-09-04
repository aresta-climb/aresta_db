## Why

O processo atual de lançamento do Editor Aresta compila o executável via PyInstaller, empacota o MSIX e disponibiliza o artefato no GitHub, mas a etapa de publicação para a Microsoft Store estava desativada no workflow do GitHub Actions (`.github/workflows/release-editor.yml`). Como o aplicativo já foi revisado, aprovado e publicado na loja com o Store ID oficial `9N6CQNH78WN8`, é necessário habilitar o upload automático seguro via MSStore CLI, permitindo escolher entre submissão direta para certificação ou envio em modo rascunho (`--noCommit`), além de sincronizar o Store ID oficial no serviço in-app (`servico_loja.py`).

## What Changes

- **Parametrização no Workflow**: Adição do parâmetro `should_publish` (booleano com padrão `true`) no gatilho `workflow_dispatch` de `.github/workflows/release-editor.yml`.
- **Publicação Automatizada no CI/CD**: Remoção do passo legado `azure/login` (OIDC) e ativação do comando `msstore publish EditorAresta.msix -id ${{ secrets.AZURE_EDITOR_ARESTA_STORE_ID }}` com injeção condicional de `--noCommit` caso `should_publish` seja falso.
- **Atualização do Store ID Canônico**: Atualização da constante `ID_PRODUTO_PADRAO` em `editor/core/servico_loja.py` para o ID oficial `9N6CQNH78WN8`, garantindo que os links de atualização e checagem in-app apontem para o produto correto na loja.
- **Testes e Validação**: Atualização dos testes unitários de `servico_loja_test.py` para refletir o Store ID canônico e validação do fluxo do workflow.

## Capabilities

### New Capabilities
<!-- Nenhuma nova capability introduzida; trata-se da evolução de capacidades existentes -->

### Modified Capabilities
- `editor-cicd-pipeline`: Automatiza o envio do pacote MSIX para a Microsoft Store no pipeline de lançamento, suportando publicação imediata para certificação ou envio como rascunho (`--noCommit`).
- `publish-version-guard`: Atualiza o identificador padrão de produto da Microsoft Store para o ID oficial do Editor Aresta (`9N6CQNH78WN8`).

## Impact

- **Código modificado**:
  - `.github/workflows/release-editor.yml`: Ajuste nos inputs e no step `Publish to MS Store`.
  - `editor/core/servico_loja.py`: Atualização do `ID_PRODUTO_PADRAO`.
  - `editor/core/servico_loja_test.py`: Verificação do ID oficial nos testes unitários.
- **Infraestrutura**:
  - Utilização dos 5 segredos configurados no repositório GitHub para autenticação via MSStore Developer CLI.
