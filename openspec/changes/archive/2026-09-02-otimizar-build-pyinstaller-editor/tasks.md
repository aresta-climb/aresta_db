## 1. Ajuste de Dependências (Library-First)

- [x] 1.1 Atualizar `pyproject.toml` substituindo `pyside6` por `pyside6-essentials` no grupo `editor`
- [x] 1.2 Sincronizar o ambiente com `uv sync` e verificar a execução de todos os testes unitários do editor com `pyside6-essentials`

## 2. Testes em Primeiro Lugar (TDD) para Lógica de Build

- [x] 2.1 [RED] Escrever testes unitários em `editor/build_test.py` para as funções puras de build (`obter_argumentos_pyinstaller`, `filtrar_binarios_desnecessarios` e `obter_modulos_excluidos`)
- [x] 2.2 [RED] Escrever teste de integração em `editor/build_test.py` para validação do tamanho máximo do executável compilado (< 95MB)
- [x] 2.3 [GREEN] Implementar a modularização das funções em `editor/build.py` e a lógica de exclusão no `editor/EditorAresta.spec` fazendo os testes passarem
- [x] 2.4 [REFACTOR] Refatorar a estrutura do `editor/build.py` e `EditorAresta.spec` garantindo código declarativo, limpo e sem abstrações desnecessárias

## 3. Integração, Validação e Cobertura 100%

- [x] 3.1 Executar a compilação completa do executável (`editor/build.py dist`) em ambiente isolado e verificar que o `.exe` gerado tem tamanho <= 90MB
- [x] 3.2 Validar que o executável gerado inicializa a interface gráfica com sucesso
- [x] 3.3 Executar `pytest editor/build_test.py --cov=editor.build --cov-report=term-missing` e garantir 100% de cobertura de testes unitários
- [x] 3.4 Executar a suíte completa de testes do editor (`pytest editor/`) garantindo 100% de sucesso
