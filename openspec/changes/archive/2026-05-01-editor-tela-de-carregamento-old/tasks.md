## 1. Diálogo de Busca de Croquis Oficiais

- [x] 1.1 Criar `editor/views/dialogo_busca_croqui_test.py` com cenários de busca e filtragem.
- [x] 1.2 Implementar `editor/views/dialogo_busca_croqui.py` com `QLineEdit` e `QListWidget`.
- [x] 1.3 Implementar lógica de leitura do arquivo `appdata/aresta_db/generated/indice.binarypb` para popular o diálogo.

## 2. Lógica de Negócio para Croquis Experimentais

- [x] 2.1 Atualizar `editor/core/croqui_experimental_test.py` com teste para `criar_croqui_a_partir_de_oficial`.
- [x] 2.2 Implementar `GerenciadorCroquiExperimental.criar_croqui_a_partir_de_oficial` que usa `criar_croqui`, copia os arquivos do banco oficial e realiza um commit inicial.

## 3. Integração na Tela de Carregamento

- [x] 3.1 Atualizar `editor/views/tela_de_carregamento_test.py` para validar as novas interações.
- [x] 3.2 Implementar slot para "Novo croqui" com solicitação de ID via `QInputDialog`.
- [x] 3.3 Implementar slot para "Importar croqui experimental" usando `QFileDialog`.
- [x] 3.4 Implementar slot para "Editar croqui oficial" integrando o `DialogoBuscaCroqui` e exibindo um `QProgressDialog` durante a cópia.
- [x] 3.5 Implementar slot para abertura de croqui por duplo clique na lista.

## 4. Refinamento e Validação
- [x] 4.1 Garantir que a lista de histórico seja atualizada após cada operação.
- [x] 4.2 Verificar se todos os arquivos seguem o princípio "Tudo em Português".
- [x] 4.3 Validar que cada arquivo `.py` possui seu correspondente `_test.py`.

## 5. Otimizações de UX e Robustez (Finalizado)
- [x] 5.1 Implementar `DialogoProgressoLog` para feedback em tempo real das operações de deploy.
- [x] 5.2 Implementar ordenação cronológica decrescente no histórico.
- [x] 5.3 Tornar a interface responsiva e maximizável (Layout Stretch).
- [x] 5.4 Adicionar lógica de normalização de ZIP e inicialização automática de Git na importação.
- [x] 5.5 Implementar rollback (limpeza automática) em caso de falha na criação/importação.
- [x] 5.6 Adicionar retry loops para compatibilidade com sistema de arquivos Windows.
