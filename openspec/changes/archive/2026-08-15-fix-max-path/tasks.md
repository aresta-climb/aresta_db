## 1. Configuração do Manifesto (MSIX)

- [x] 1.1 Adicionar namespace `ws2` e `longPathAware` no `AppxManifest.xml`

## 2. Refatoração de Diretórios Base

- [x] 2.1 Adicionar chamada para `app.setApplicationName("EditorAresta")` no `editor/main.py`
- [x] 2.2 Modificar `editor/core/storage.py` para usar apenas `Path(appdata)` e evitar o subdiretório redundante `editor_aresta`
- [x] 2.3 Modificar `obter_caminho_croquis_experimentais` para retornar a subpasta `croquis` em vez de `croquis_experimentais`

## 3. Lógica de Croquis e IDs

- [x] 3.1 Importar `uuid` em `editor/core/croqui_experimental.py` e gerar nomes de pasta para projetos novos utilizando `uuid.uuid4().hex[:8]`
- [x] 3.2 Atualizar `editor/legacy_views/tela_de_carregamento.py` para ordenar os croquis locais por data de edição (presente nos metadados), em vez de ordem alfabética de pasta
- [x] 3.3 Atualizar `WidgetItemHistorico` em `tela_de_carregamento.py` para exibir o ID físico (8-chars) da pasta na interface
- [x] 3.4 (TDD) Escrever ou atualizar testes em `tela_de_carregamento_test.py` para garantir que 100% dessas lógicas (ordenação e exibição de ID) estejam cobertas antes da implementação final

## 4. Segurança do Git com pygit2

- [x] 4.1 Substituir `pygit2.clone_repository` por `pygit2.init_repository` com injeção de `core.longpaths = True`
- [x] 4.2 Completar o fluxo de `clone` efetuando o `fetch` manual do remote e depois realizando o `checkout`
- [x] 4.3 Garantir que os testes da camada de `sync` que faziam assert no mock de `clone_repository` continuem passando para a nova lógica
