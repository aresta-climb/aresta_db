## Why

Atualmente, o script `scripts/editar_imagens.py` funciona apenas de forma independente, o que fragmenta a experiência do usuário ao editar um croqui no aplicativo Aresta Editor. Integrar esta funcionalidade diretamente na área principal do editor (aba "Imagens") aumentará a produtividade e centralizará as ferramentas de edição.

## What Changes

- **Refatoração de `scripts/editar_imagens.py`**: O código será reorganizado para separar a lógica da interface (Widget) da lógica de aplicação (Janela Principal autônoma).
- **Novo Widget `WidgetEditorImagens`**: Criação de um componente reutilizável que encapsula a funcionalidade de edição de imagens.
- **Integração na Janela Principal do Editor**: A aba "Imagens" da barra lateral passará a carregar o `WidgetEditorImagens` na área central.
- **Gerenciamento de Salvamento**: 
    - Quando rodando como script autônomo, o botão "Salvar" continua visível.
    - Quando integrado no Editor, o botão "Salvar" interno é ocultado e a ação de salvamento é vinculada ao botão "Salvar" global da barra de ferramentas superior.
- **Suporte a CLI**: Manutenção da capacidade de rodar o script independentemente passando o caminho do croqui.

## Capabilities

### New Capabilities
- `editor-imagens`: Fornecer uma interface integrada para edição de imagens (crop, rotação, máscaras) dentro do editor Aresta, com suporte a fluxo de trabalho em lote.

### Modified Capabilities
- `editor-area-principal`: Atualizar a navegação da barra lateral para ativar a aba de imagens e gerenciar o ciclo de vida do widget de edição de imagens.

## Impact

- **`scripts/editar_imagens.py`**: Grande refatoração para extrair o widget.
- **`editor/views/janela_principal.py`**: Modificação para instanciar e gerenciar o novo widget.
- **`editor/views/widget_editor_imagens.py`**: [NOVO] Local onde residirá a classe refatorada do widget.
- **APIs de Salvamento**: Necessidade de expor um método de salvamento no widget para ser chamado pela Janela Principal.
