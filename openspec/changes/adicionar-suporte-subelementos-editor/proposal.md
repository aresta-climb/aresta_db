## Por Que (Why)

Atualmente, ao abrir um croqui recém-criado ou selecionar mensagens que possuem listas repetidas vazias (como `Croqui.picos`, `Pico.setores_ou_grupos`, `Grupo.setores` ou `Setor.escaladas`), a árvore de navegação omite completamente essas coleções porque o adaptador só cria nós agrupadores quando a lista possui um ou mais elementos. Como o formulário da direita também omite esses campos por delegar a hierarquia para a árvore, o usuário fica impossibilitado de adicionar setores, grupos, escaladas ou botões a entidades recém-criadas.

Esta proposta visa resolver essa limitação seguindo rigorosamente as diretrizes de engenharia de software de `PRINCIPIOS.md` (Tudo em Português, TDD, Testes de Integração em Primeiro Lugar, 100% de Cobertura, Simplicidade e Mutações de Estado estritamente via Histórico Undo/Redo).

## O Que Muda (What Changes)

- **Exibição de Expandos e Nós Virtuais para Coleções Vazias**: O adaptador da árvore (`ProtobufTreeViewAdapter`) passa a inspecionar os descritores do Protobuf e exibir os nós agrupadores (expandos) e o nó virtual interativo `+ Adicionar [Tipo]` mesmo quando a lista estiver com 0 elementos.
- **Diálogo Modal para Campos ONEOF na Árvore**: Ao acionar o nó virtual de adição de campos com múltiplos tipos possíveis (ex: `SetorOuGrupo` ou `Escalada`), o sistema exibe um diálogo de seleção permitindo ao usuário escolher o tipo desejado (ex: Setor vs Grupo).
- **Menu de Contexto Estendido na Árvore**: Adiciona opções no clique com o botão direito nos nós estruturais (`Croqui`, `Pico`, `Grupo`, `Setor`) para permitir a adição direta de seus sub-elementos filhos (ex: "Adicionar Setor ou Grupo..."), despachando comandos através do histórico Undo/Redo.
- **Cartões de Ação Rápida no Rodapé dos Formulários**: O formulário da direita (`WidgetFormularioPadrao`) passa a renderizar cartões contextuais simples e declarativos no rodapé de entidades que possuem sub-elementos (`Croqui`, `Pico`, `Grupo`, `Setor`, `ViaMultiplasEnfiadas`), exibindo a contagem de itens e botão de atalho para adicionar novos elementos filhos via histórico Undo/Redo.

## Capacidades (Capabilities)

### New Capabilities
<!-- Nenhuma nova capability isolada; as modificações aprimoram as capacidades existentes de árvore e formulário. -->

### Modified Capabilities
- `editor-dados-arvore`: Atualização dos requisitos de detecção e renderização de expandos vazios, nós virtuais de adição e menus de contexto para adição em nós pais.
- `editor-dados-formularios`: Adição de requisito para renderização de cartões/seções de ação rápida para sub-elementos no rodapé dos formulários.

## Impacto (Impact)

- **Código Afetado**: `editor/views/tree_view_adapter.py`, `editor/views/widget_editor_dados.py` e seus respectivos arquivos de teste (`tree_view_adapter_test.py`, `widget_editor_dados_test.py`).
- **Nomenclatura**: 100% em português brasileiro para todas as variáveis, funções, classes, sinais e documentações, em conformidade com o Princípio I.
- **Histórico Undo/Redo**: 100% das mutações de estado realizadas através do `CroquiController` e pilha `QUndoStack`, em conformidade com o Princípio VII.
- **Cobertura de Testes**: 100% de cobertura de testes unitários e de integração, em conformidade com os Princípios III, IV e V.
