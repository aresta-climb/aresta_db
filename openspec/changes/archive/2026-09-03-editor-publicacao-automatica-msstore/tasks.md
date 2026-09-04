## 1. Atualização do Serviço de Loja (TDD)

- [x] 1.1 Atualizar testes em `editor/core/servico_loja_test.py` para validar o Store ID oficial `9N6CQNH78WN8`
- [x] 1.2 Atualizar `ID_PRODUTO_PADRAO = "9N6CQNH78WN8"` em `editor/core/servico_loja.py`
- [x] 1.3 Executar a suíte de testes de `editor/core/servico_loja_test.py` e garantir 100% de aprovação

## 2. Ajuste do Workflow de Release no GitHub Actions

- [x] 2.1 Adicionar input `should_publish` (booleano, default true) no gatilho `workflow_dispatch` de `.github/workflows/release-editor.yml`
- [x] 2.2 Remover step legado de autenticação OIDC `Login to Azure (OIDC)`
- [x] 2.3 Atualizar o step `Publish to MS Store` para montar os argumentos dinamicamente, executar `msstore publish` e anexar `--noCommit` caso `should_publish` seja falso

## 3. Validação e Verificação Global

- [x] 3.1 Executar a suíte de testes unitários do editor (`uv run pytest editor/core/servico_loja_test.py`)
- [x] 3.2 Executar a suíte completa de testes do repositório
- [x] 3.3 Validar a sintaxe do arquivo de workflow `.github/workflows/release-editor.yml`
