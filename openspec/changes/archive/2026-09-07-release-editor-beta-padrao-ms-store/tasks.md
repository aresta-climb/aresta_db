## 1. Testes Automatizados do Workflow (TDD)

- [x] 1.1 Atualizar `tests/workflow_release_editor_test.py` com testes para validar a presença do input `publicar_microsoft_store` (tipo booleano, padrão `false`) e a remoção de `should_publish`, confirmando falha inicial na execução com `uv run pytest tests/workflow_release_editor_test.py`.
- [x] 1.2 Adicionar testes em `tests/workflow_release_editor_test.py` validando a existência da condicional `if: ${{ inputs.publicar_microsoft_store }}` nos passos da Microsoft Store e a ausência de `--noCommit` no comando `msstore publish`.
- [x] 1.3 Adicionar testes em `tests/workflow_release_editor_test.py` verificando a ordenação das etapas, assegurando que o canal Beta é processado antes dos passos de produção e da Microsoft Store.

## 2. Refatoração do Workflow de Release

- [x] 2.1 Atualizar a seção `inputs` em `.github/workflows/release-editor.yml`, substituindo `should_publish` por `publicar_microsoft_store` com descrição clara e valor padrão `false`.
- [x] 2.2 Reordenar as etapas no arquivo `.github/workflows/release-editor.yml` para posicionar a compilação, assinatura e publicação do canal Beta logo após os testes unitários.
- [x] 2.3 Mover as etapas de compilação de produção, geração do MSIX oficial e publicação na loja para depois do canal Beta, configurando a condicional `if: ${{ inputs.publicar_microsoft_store }}` em cada uma delas.
- [x] 2.4 Atualizar o script de execução do `msstore publish` em `.github/workflows/release-editor.yml`, removendo o uso de `--noCommit` para comitar a submissão diretamente para revisão.

## 3. Validação e Verificação

- [x] 3.1 Executar os testes automatizados do workflow via `uv run pytest tests/workflow_release_editor_test.py -v` e garantir que todos passem com sucesso.
- [x] 3.2 Validar a integridade da especificação via `openspec validate release-editor-beta-padrao-ms-store --strict`.
