## Implementation Tasks

Todos os testes listados abaixo DEVEM cobrir 100% das lógicas introduzidas e seguir rigorosamente a prática de TDD (Test-Driven Development).

- [x] **1. Refatoração do `comprimir_imagens.py`**
  - **[TDD]** Criar/atualizar `comprimir_imagens_test.py` com testes para uma função puramente em memória (`comprimir_imagem_para_bytes`), validando regras de redimensionamento (área máx 2048*2048 pixels) e qualidade (WebP-85).
  - Criar a função `comprimir_imagem_para_bytes(imagem_path_ou_bytes, quality=85, max_area=4194304) -> bytes`.
  - Adaptar o `comprimir_imagem()` atual para utilizar a nova função `comprimir_imagem_para_bytes()`.
  - Validar se a compressão em memória funciona e mantém as mesmas regras, garantindo 100% de cobertura nos testes.

- [x] **2. Implementação do `CmdAdicionarMapaArquivo`**
  - **[TDD]** Escrever testes isolados em `comandos_mapas_test.py` para verificar o funcionamento do undo e redo combinando modificações do modelo e manipulação de arquivos no disco (com mocking de file system).
  - Criar novo comando de Undo (`CmdAdicionarMapaArquivo`) em `editor/commands/comandos_mapas.py` ou similar.
  - Construtor deverá receber os bytes da imagem final.
  - `redo()`: Escreve o arquivo no caminho predefinido e chama a inserção no `CroquiModel`.
  - `undo()`: Remove a inserção no `CroquiModel` e deleta o arquivo local de `imagens/`.
  - Adicionar o método `adicionar_mapa_com_arquivo(...)` no `CroquiController`, com respectivos testes no controlador (`croqui_controller_test.py`).

- [x] **3. Criação do `DialogoAdicionarMapa`**
  - **[TDD]** Escrever testes em `dialogo_adicionar_mapa_test.py` que garantam a inicialização correta com o nome de arquivo, a não-subscrição de arquivos existentes e o fluxo de preview.
  - Implementar nova classe `DialogoAdicionarMapa` em `editor/views/dialogos/dialogo_adicionar_mapa.py`.
  - Interface baseada em `QDialog` com área para arrastar ou selecionar imagem (Drag and Drop / Clique).
  - Campo de texto para o nome do arquivo, que inicia pré-preenchido com o nome gerado.
  - Exibição de preview da imagem após selecionada.
  - Validação: ao clicar em "OK", se o arquivo já existir em disco, mostrar um erro e retornar falso.

- [x] **4. Interceptação do clique em "Adicionar Item"**
  - **[TDD]** Adicionar testes em `widget_editor_dados_test.py` para garantir que o clique no repetidor de `Mapa` despacha a lógica nova ao invés da criação limpa, validando a sugestão de nome de arquivo `grupo_<nome_grupo>_setor_<nome_setor>_p<index>.webp`.
  - Em `WidgetEditorDados.ContainerRepeatedWidget._on_add_clicked`, detectar se a mensagem é do tipo `Mapa`.
  - Obter referências hierárquicas (Setor e Grupo) para formatar o nome sugerido.
  - Abrir o `DialogoAdicionarMapa`.
  - Se aceito, ler os bytes da imagem, usar `comprimir_imagem_para_bytes` para obter o array final comprimido, as dimensões finais e acionar o `CroquiController.adicionar_mapa_com_arquivo(...)` configurando os campos de `caminho_imagem_mapa`, `largura_mapa` e `altura_mapa` automaticamente.
