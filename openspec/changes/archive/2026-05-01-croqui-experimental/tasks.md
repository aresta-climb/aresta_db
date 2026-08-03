## 1. Protobuf Definitions

- [x] 1.1 Criar a mensagem `CroquiExperimental` no arquivo `aresta_api/proto/croqui_experimental.proto`.
- [x] 1.2 Atualizar o processo de build do Protobuf (se necessário) para incluir o novo arquivo.

## 2. Gerenciamento de Arquivos Locais

- [x] 2.1 Criar utilitário no Editor Aresta para inicializar e gerenciar a pasta `croquis_experimentais` no storage local.
- [x] 2.2 Criar função para criar o diretório e sub-diretórios (`database/`, `compilado/`) a partir dos metadados de um croqui experimental.

## 3. Controle de Versão

- [x] 3.1 Implementar função de inicialização do Git local (`git init`) programaticamente para a pasta raiz do croqui recém-criado usando pygit2.

## 4. Importação e Exportação

- [x] 4.1 Implementar função de exportação compactando a pasta do croqui experimental em formato `.zip` renomeado para `.croqui`.
- [x] 4.2 Implementar função de importação que descompacte um arquivo `.croqui` diretamente em `croquis_experimentais`.
