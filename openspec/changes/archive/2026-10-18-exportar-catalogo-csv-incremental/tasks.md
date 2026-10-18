# Tasks

## 1. Preservação Incremental do SQLite (`catalogo.db`) e Limpeza de Órfãos

- [x] 1.1 Escrever testes comportamentais em `scripts/gerar_catalogo_sqlite_lib_test.py` (fase Red do TDD) verificando que `gerar_catalogo_completo()` não modifica `atualizado_em` nem os bytes de `catalogo.db` quando um croqui alvo é recompilado sem alteração nos metadados do catálogo, e que croquis órfãos são removidos quando `alvos=None`, validando a falha inicial com `uv run pytest scripts/gerar_catalogo_sqlite_lib_test.py`
- [x] 1.2 Implementar em `scripts/gerar_catalogo_sqlite_lib.py` (fase Green/Refactor) a verificação de igualdade dos dados de catálogo por `croqui_uid`, a inicialização sem commit redundante quando o schema já está íntegro e a remoção de `croqui_uid` órfãos em compilação completa (`alvos=None`), confirmando que os testes passam com `uv run pytest scripts/gerar_catalogo_sqlite_lib_test.py`

## 2. Exportação Incremental Determinística em CSV (`catalogo_croquis.csv`, `catalogo_aresta.csv`, `catalogo_meta.csv`)

- [x] 2.1 Escrever testes comportamentais em `scripts/gerar_catalogo_sqlite_lib_test.py` (fase Red do TDD) verificando a criação e ordenação de `catalogo_croquis.csv`, `catalogo_aresta.csv` e `catalogo_meta.csv`, bem como o short-circuit que preserva os arquivos CSV intocados quando nenhum dado do catálogo muda, validando a falha inicial com `uv run pytest scripts/gerar_catalogo_sqlite_lib_test.py`
- [x] 2.2 Implementar `exportar_catalogo_csv()` e sua integração com `gerar_catalogo_completo()` em `scripts/gerar_catalogo_sqlite_lib.py` (fase Green/Refactor), verificando 100% de cobertura comportamental com `uv run pytest scripts/gerar_catalogo_sqlite_lib_test.py --cov=scripts.gerar_catalogo_sqlite_lib --cov-report=term-missing`

## 3. Geração dos Artefatos em `generated/` e Validação Final

- [x] 3.1 Executar `uv run scripts/deploy_generated.py --no-status` para gerar `generated/catalogo_croquis.csv`, `generated/catalogo_aresta.csv` e `generated/catalogo_meta.csv` e verificar com uma segunda execução que `generated/catalogo.db` e os 3 CSVs permanecem 100% inalterados
