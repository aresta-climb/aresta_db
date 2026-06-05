## 1. Setup Inicial e Empacotamento

- [x] 1.1 Criar a estrutura base de pacotes em `editor/` e configurar gerenciamento de dependências (`PyQt6`, `PyInstaller`, `GitPython`).
- [x] 1.2 Criar os testes iniciais e mock de execução para o pipeline de CI validando a compilação do executável usando PyInstaller.
- [x] 1.3 Implementar o script de empacotamento (`build.py`) utilizando PyInstaller com testes de unidade orientados a TDD em `editor/build_test.py`.

## 2. Inicialização e Bibliotecas Core (Library-First & TDD)

- [x] 2.1 Criar a biblioteca base `editor/core/storage.py` com testes de unidade orientados a TDD em `editor/core/storage_test.py` garantindo a resolução correta dos diretórios locais via `QStandardPaths`.
- [x] 2.2 Criar testes de integração para o processo de clone do repositório `aresta_db` local.
- [x] 2.3 Implementar a rotina de inicialização no módulo `storage.py` que cria os diretórios base e faz o clone inicial/pull usando `GitPython`.

## 3. Interface da Janela Principal (Integration Tests First)

- [x] 3.1 Adicionar infraestrutura de testes para widgets PyQt6 (ex: uso do `pytest-qt`).
- [x] 3.2 Criar testes de integração verificando a correta inicialização do `QMainWindow`, garantindo a existência do `QSplitter` com a barra lateral e a área principal.
- [x] 3.3 Implementar a classe de Janela Principal (Main Window) contendo o layout base e integrar ao script `main.py`.

## 4. Página Inicial (Simplicidade e Anti-Abstração)

- [x] 4.1 Criar testes automatizados da Página Inicial, garantindo que os três botões principais e a lista de croquis sejam renderizados.
- [x] 4.2 Implementar os componentes de interface da Página Inicial: botões "Novo croqui", "Importar croqui experimental" e "Editar croqui oficial" com callbacks em formato de mocks simples (`print` no terminal).
- [x] 4.3 Escrever testes para leitura do sistema de arquivos e população da lista de croquis experimentais da UI.
- [x] 4.4 Implementar a rotina que varre o diretório `croquis_experimentais`, extrai os nomes e datas, e preenche a lista interativa da Página Inicial, concluindo a integração da view com a biblioteca de storage.
