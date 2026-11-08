# Views

As Views aqui contidas devem ser "Burras".
Isso significa que elas NÃO contêm lógica de negócio e NÃO manipulam os dados diretamente.

**Regras:**
1. **Puxar (Pull):** A View lê do Model (`get_nome()`) para renderizar seu estado inicial.
2. **Ouvir (Push):** A View assina os Sinais emitidos pelo Model para se atualizar automaticamente quando os dados mudam em background (Undo/Redo).
3. **Sem Mutação:** Views NUNCA chamam os métodos `_set_*` ou `definir_imagem_memoria` do Model diretamente.
4. **Despachar Ações:** Quando o usuário clica ou digita algo, a View apenas despacha a sua intenção ao Controller (`controller.alterar_campo_imagem(...)`, `controller.substituir_imagem_mapa(...)`), sem saber ou se importar de como os dados serão armazenados.

## Fluxo Unificado de Entrada e Substituição de Imagens

Todos os pontos de entrada e substituição de imagens do editor utilizam os diálogos com a experiência unificada de duas abas (`"Importar Nova Imagem"` com Drag & Drop, pré-visualização, recorte interativo *rubber-band* e metadados de resolução/tamanho WebP; e `"Imagens do Croqui"` com galeria pesquisável em disco e RAM):

- **`dialogos/dialogo_adicionar_mapa.py` (`DialogoAdicionarMapa`)**: Wizard unificado utilizado para:
  - Adicionar novos mapas ou substituir a imagem de um mapa existente (`modo_substituicao_mapa=True`) no `WidgetEditorDados` (`WidgetCardMapa` e visão de nó `MAPA`) e no `WidgetEditorMapas`, oferecendo a opção de reajustar proporcionalmente as coordenadas dos POIs quando a resolução muda.
  - Selecionar ou trocar imagens de campos Protobuf no `WidgetCampoImagem` (com suporte a destino fixo como `thumbnail.webp` e orçamento de área customizado).
  - Substituir imagens selecionadas no `WidgetEditorImagens` em modo de destino fixo.
- **`dialogos/dialogo_inserir_imagem_markdown.py` (`DialogoInserirImagemMarkdown`)**: Diálogo de inserção de imagens em campos Markdown (`![alt](imagens/...)`), compartilhando os mesmos recursos de Drag & Drop, recorte interativo e seleção da galeria `"Imagens do Croqui"`.
