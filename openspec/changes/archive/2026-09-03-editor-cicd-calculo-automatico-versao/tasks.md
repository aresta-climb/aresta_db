## 1. Implementação da Ferramenta de Cálculo de Versão com TDD (100% Cobertura)

- [x] 1.1 Criar suite de testes unitários `editor/release_tools/calculate_release_version_test.py` cobrindo cenários patch, minor, major, custom, validação SemVer, CLI e leitura de arquivo (Fase Red)
- [x] 1.2 Implementar biblioteca `editor/release_tools/calculate_release_version.py` para passar todos os testes (Fase Green)
- [x] 1.3 Validar 100% de cobertura de testes unitários com pytest-cov

## 2. Integração no Workflow do GitHub Actions

- [x] 2.1 Atualizar `inputs` em `.github/workflows/release-editor.yml` adicionando `bump_type` (choice: patch, minor, major, custom) e `custom_version`
- [x] 2.2 Adicionar etapa no job para calcular a versão oficial e repassar `${{ steps.versao.outputs.versao }}` para as etapas de build, tag, MSIX e publish

## 3. Validação e Verificação Global

- [x] 3.1 Executar a suíte de testes de release_tools e do editor
- [x] 3.2 Validar sintaxe do workflow `.github/workflows/release-editor.yml`

