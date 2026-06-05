## 1. Infraestrutura Global

- [x] 1.1 Criar a biblioteca `core/historico.py` com o gerenciador da pilha de undo/redo baseada no padrão Command.
- [x] 1.2 Criar os testes unitários (`historico_test.py`) garantindo o funcionamento do push, undo, redo e merge das instâncias de Command.
- [x] 1.3 Instanciar o `QUndoStack` global em `JanelaPrincipal` (`area_principal.py`) e conectá-lo às `QAction` globais já existentes (`acao_desfazer`, `acao_refazer`).
- [x] 1.4 Criar testes de integração (`area_principal_historico_test.py`) garantindo que os atalhos globais acionam corretamente a pilha de testes mock.
- [x] 1.5 Atualizar o documento `PRINCIPIOS.md` para incluir a regra inegociável de que edições de estado na interface do usuário devem ser feitas através de Comandos de Histórico.
- [x] 1.6 Implementar a estrutura de "Lixeira Interna" (`.trash_interna`) no `GerenciadorCaminhos` (`storage.py`) para evitar deleção definitiva de arquivos.
- [x] 1.7 Criar comando genérico `CmdRemoverArquivoFisico` que utilize a "Lixeira Interna", permitindo restaurar arquivos deletados (imagens, markdowns, etc).

## 2. Comandos Protobuf (Aba de Dados)

- [x] 2.1 Criar a biblioteca base para comandos de Protobuf, contendo `CmdAlterarPrimitivo` (com lógica de `mergeWith`), `CmdAdicionarRepeated`, `CmdRemoverRepeated` e `CmdAlterarOneof`.
- [x] 2.2 Escrever testes unitários exaustivos garantindo que cada comando reverte com perfeição alterações numa mensagem `Croqui` arbitrária em memória.
- [x] 2.3 Refatorar `WidgetFormularioPadrao` para instanciar a classe `AtualizadorUI`, que controla a restauração do foco do input após uma operação destrutiva de UI (Undo).
- [x] 2.4 Modificar a fábrica de formulários primitivos (`_setup_primitive_widget`) para desativar `setUndoRedoEnabled(False)` dos campos de texto numéricos e de strings.
- [x] 2.5 Substituir as mutações diretas em `_render_field`, `_render_repeated_field` e `_render_oneof` pelo envio dos comandos à pilha global.
- [x] 2.6 Criar teste de integração conectando uma alteração no UI da aba de Dados até o registro do comando na pilha global e sua execução.

## 3. Comandos de Gráficos e Arquivos (Abas Mapas e Imagens)

- [x] 3.1 Criar comando `CmdMoverPonto` para os bounding boxes e pontos em `editor_mapas.py`, interceptando as ações com os eventos `mousePressEvent` e `mouseReleaseEvent`.
- [x] 3.2 Criar comando `CmdMoverImagem` para o `CropBoxItem` em `widget_editor_imagens.py` (idêntico conceito do mapa).
- [x] 3.3 Escrever testes unitários (`comandos_graficos_test.py`) acionando o undo e redo e verificando se os vértices/caixas são revertidos.
- [x] 3.4 Escrever teste de integração de ponta a ponta simulando o drag de um item de mapa, seguido por Ctrl+Z.

