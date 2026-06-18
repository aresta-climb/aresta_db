## 1. Criação das Abstrações Base (TDD)

- [x] 1.1 Criar suite de testes `tests/editor/core/workspace_test.py` definindo os comportamentos esperados (100% test coverage target).
- [x] 1.2 Criar módulo `editor/core/workspace.py` com a interface abstrata `EditorWorkspace`.
- [x] 1.3 Implementar a classe `ExperimentalWorkspace` contendo o comportamento atual (compilação e commit via pygit2), fazendo os testes passarem.
- [x] 1.4 Implementar a classe `LocalRepoWorkspace` contendo as regras locais, incluindo a lógica de `git mv` simulada nos testes.

## 2. Refatoração da Janela Principal

- [x] 2.1 Modificar o construtor da `JanelaPrincipal` (`editor/legacy_views/area_principal.py`) para utilizar a instância de `EditorWorkspace` e remover dependência direta do `GerenciadorCroquiExperimental`.
- [x] 2.2 Substituir todas as referências rígidas de `self.caminho_croqui / "database"` por chamadas aos métodos de path da interface do workspace.
- [x] 2.3 Substituir a lógica de persistência e compilação em `salvar_croqui` pelas rotinas do workspace ativo.
- [x] 2.4 Atualizar `_exibir_conexao_celular` para buscar a rota de saída compilada através do workspace.
- [x] 2.5 Modificar a UI para desabilitar o botão "Publicar" (ficando cinza) caso `can_publish_pr` seja false.
- [x] 2.6 Adicionar a tag `[Local Mode]` no título da janela caso o workspace atual seja `LocalRepoWorkspace`.

## 3. Adaptações nas Páginas e Componentes

- [x] 3.1 Garantir que `PaginaMapas.carregar_mapas` utilize corretamente o path do database injetado pelo workspace.
- [x] 3.2 Atualizar `PaginaImagens.carregar_imagens` e salvar imagens para respeitar as definições do workspace ativo (algumas páginas podem assumir pastas que agora precisam ser relativas ao path abstraído).

## 4. Integração na Camada de Inicialização CLI

- [x] 4.1 Ajustar a captura de argumentos em `editor/main.py` para detectar diretórios iniciados pela tag 'database' nos parâmetros.
- [x] 4.2 Codificar a ramificação da inicialização para criar o contexto "LocalRepo", pulando a autenticação do GitHub e a tela de carga inicial.
- [x] 4.3 Fazer testes fim-a-fim validando as interações no ambiente local (edição e alteração do ID).
