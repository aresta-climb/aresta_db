## 1. Movimentação de Arquivos Fonte

- [x] 1.1 Mover `editor/views/area_principal.py` para `editor/legacy_views/area_principal.py`
- [x] 1.2 Mover `editor/views/tela_de_carregamento.py` para `editor/legacy_views/tela_de_carregamento.py`
- [x] 1.3 Mover `editor/views/dialogo_busca_croqui.py` para `editor/legacy_views/dialogo_busca_croqui.py`
- [x] 1.4 Mover `editor/views/dialogo_conexao_celular.py` para `editor/legacy_views/dialogo_conexao_celular.py`

## 2. Movimentação de Testes

- [x] 2.1 Mover `editor/views/area_principal_test.py` (e conexos como `area_principal_e2e_test.py`, etc) para `editor/legacy_views/`
- [x] 2.2 Mover `editor/views/tela_de_carregamento_test.py` para `editor/legacy_views/`
- [x] 2.3 Mover `editor/views/dialogo_busca_croqui_test.py` para `editor/legacy_views/`
- [x] 2.4 Mover `editor/views/dialogo_conexao_celular_test.py` para `editor/legacy_views/`

## 3. Correção de Imports

- [x] 3.1 Substituir imports de `area_principal` (ex: `from editor.views.area_principal`) para o novo caminho no projeto (`main.py` e afins)
- [x] 3.2 Substituir imports de `tela_de_carregamento` para o novo caminho
- [x] 3.3 Substituir imports de `dialogo_busca_croqui` para o novo caminho
- [x] 3.4 Substituir imports de `dialogo_conexao_celular` para o novo caminho

## 4. Validação

- [x] 4.1 Executar os testes localmente (`pytest`) para confirmar que nenhum import foi quebrado.
- [x] 4.2 Executar o aplicativo Editor Aresta para validar que as telas continuam renderizando perfeitamente nas posições originais.
