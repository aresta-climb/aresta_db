## Why

Atualmente, o `editor_mapas` funciona como um componente legado monolítico. Ele gerencia seu próprio estado lendo e escrevendo arquivos Markdown separadamente, mantém um controle de Undo/Redo isolado e não se beneficia do ecossistema central do aplicativo. A migração deste componente para a arquitetura MVC padrão (com `CroquiModel`, `CroquiController` e formulários centralizados) é essencial para garantir um histórico global de ações consistente, eliminar código duplicado de manipulação de arquivos e unificar a experiência do usuário entre a edição de dados textuais e as anotações visuais nos croquis.

## What Changes

- **Integração MVC do Editor Visual:** O `WidgetEditorMapas` atual será completamente refatorado para operar como uma *View* "burra", escutando e reagindo aos sinais emitidos pelo `CroquiModel`.
- **Interação através de Comandos Protobuf:** Ao invés de usar `CmdMoverPonto` local, qualquer alteração visual dos pontos de interesse (inserção, movimentação, redimensionamento, etc.) emitirá uma solicitação ao `CroquiController` que orquestrará a modificação no `CroquiModel` usando os mesmos comandos genéricos em Protobuf. O histórico global do aplicativo será mantido intacto.
- **Integração Direta com a Árvore de Dados:** A aba de *Mapas* se conectará fluidamente à árvore do Editor de Dados. Quando um mapa for selecionado na árvore de navegação, a View oferecerá a capacidade de abri-lo diretamente no Editor de Mapas. 
- **Nova Sidebar de Contexto:** O `WidgetEditorMapas` irá desenhar a sua barra lateral (`sidebar`) observando ativamente os nós iterados do `CroquiModel`, removendo a necessidade de leitura e observação própria de arquivos `.md` do disco (o que também permite a deleção do atual `GerenciadorArquivosMapa`).
- **Novo Campo no Protobuf:** A inserção do modo `MAPA` no enum `MensagemFormatoUi` do `croqui.proto`.
- **Desenvolvimento Guiado por Testes (TDD):** A implementação seguirá o imperativo do TDD (Red-Green-Refactor). Nenhum código de produção será escrito sem um teste unitário falho prévio, garantindo 100% de cobertura de testes na nova implementação do `WidgetEditorMapas` e do gateway no `WidgetEditorDados`.
- **Deleção de Código Antigo:** **BREAKING** Remoção de `scripts/editar_mapas.py`. Os testes existentes serão migrados e reescritos sob a nova arquitetura para manter a cobertura.

## Capabilities

### New Capabilities
- `editor-mapas-mvc-sidebar`: Geração da barra lateral do editor de mapas populada dinamicamente a partir dos objetos contidos no `CroquiModel`.
- `editor-dados-mapa-gateway`: A integração na UI da árvore principal, permitindo a exibição de um botão de ação "Abrir no Editor de Mapas" para nós da estrutura formatados com a flag `MAPA`.

### Modified Capabilities
- `editor-mapas`: Transição da edição local e salva em arquivo em tempo real, para a mutação de mensagens em memória sob controle de versão da `QUndoStack` MVC.
- `protobuf-editor-metadata`: Expansão do metadado de interface de usuário (UI) para reconhecer explicitamente os nós de Mapa.

## Impact

- **`aresta_db/editor/legacy_views/editor_mapas.py`**: Será reescrito, renomeado para `aresta_db/editor/views/widget_editor_mapas.py` (ou integrado na view correspondente) e esvaziado de dependências de leitura/gravação em disco (I/O).
- **`aresta_db/aresta_api/proto/croqui.proto`**: Receberá o novo formato da interface do usuário.
- **`aresta_db/editor/views/widget_editor_dados.py`**: Interceptará o formato `MAPA` para exibir um botão "call to action" e comunicar a troca de visibilidade/foco das views filhas.
- **Testes Unitários**: O antigo `editor_mapas_test.py` precisará de um refatoramento amplo para instanciar as views alimentadas pelo MVC mockado.
