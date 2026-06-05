## Why

A arquitetura atual da aba de Dados (como o `WidgetEditorDados`) acopla fortemente a interface gráfica (Views) com os dados subjacentes (Protobuf) e com a lógica de histórico (QUndoCommands). Isso gera fragilidade, loops de atualização difíceis de controlar e torna o código confuso. Refatorar a aba de Dados para um padrão MVC estrito (com Controllers e Commands blindados) resolverá esses gargalos, isolará o código legado, e criará uma base sustentável para a futura migração de outras áreas do editor (Mapas e Imagens).

## What Changes

- Criação de uma estrutura limpa de diretórios: `models/`, `views/`, `controllers/` e `commands/` dentro de `editor/`.
- Mover as views antigas (Mapas, Imagens, etc.) que não seguem o MVC para um diretório `legacy_views/`.
- Documentar a arquitetura com arquivos `README.md` explicativos na raiz do `editor/` e dentro de cada nova sub-pasta.
- Implementação de regras estritas de encapsulamento: classes em `models/` terão métodos de escrita "protegidos" (`_set_*`) que devem ser acessados única e exclusivamente por classes dentro da pasta `commands/`.
- Introdução de testes arquiteturais automatizados (`editor/arquitetura_mvc_test.py`) usando análise estática (AST) para garantir que Views e Controllers não mutem o Model diretamente.
- O `WidgetEditorDados` será refatorado para ser a primeira "View burra" do novo MVC, apenas escutando sinais do Model e despachando intenções para os Controllers.

## Capabilities

### New Capabilities
- `arquitetura-mvc`: Base arquitetural MVC orientada a comandos para o Aresta Editor, definindo regras estritas de encapsulamento, separação de pastas (`models`, `views`, `controllers`, `commands`) e testes estruturais.

### Modified Capabilities
- `undo-redo-protobuf`: Modifica a forma como os comandos de undo/redo são acionados e estruturados. Passarão a operar sob as regras de encapsulamento da nova camada `commands/` e coordenados pelos `controllers/`, em vez de serem gerenciados diretamente pelas views atuais.

## Impact

- **Código Afetado**: Refatoração completa de `editor/views/widget_editor_dados.py` (movido definitivamente para a sub-pasta `views/`), movimentação de `editor/core/comandos_protobuf.py` para `commands/`, e ajustes de imports em `area_principal.py`.
- **Estrutura de Diretórios**: Mudança profunda na organização de `editor/`, introduzindo `models/`, `controllers/`, `commands/` e criando a distinção clara com `legacy_views/`.
- **Testes**: Adição de novo suíte de testes de validação arquitetural via AST (`editor/arquitetura_mvc_test.py`).
