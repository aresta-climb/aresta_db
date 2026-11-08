## Context

O Editor Aresta passou recentemente por uma refatoração arquitetural MVC que consolidou todas as mutações de estado em 7 comandos canônicos (`CmdAlterarCampo`, `CmdAlterarImagem`, `CmdAlterarAnexo`, `CmdAdicionarRepeated`, `CmdRemoverRepeated`, `CmdMoverRepeated` e `CmdMacro`), validados estaticamente via AST em `editor/arquitetura_mvc_test.py`.

Contudo, a camada de entrada e substituição de imagens permaneceu dividida em quatro fluxos distintos:
1. `DialogoAdicionarMapa` (`editor/views/dialogos/dialogo_adicionar_mapa.py`): possui área de Drag & Drop (`AreaDropImagem`), barra de recorte interativo (*rubber-band crop* com `✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), painel de metadados ricos e validação de colisão, mas **não possui** a aba `"Imagens do Croqui"` (galeria) nem modo de substituição para mapas ou imagens existentes.
2. `DialogoInserirImagemMarkdown` (`editor/views/dialogos/dialogo_inserir_imagem_markdown.py`): possui duas abas (`"Importar Nova Imagem"` e `"Imagens do Croqui"`), mas **não possui** a barra de recorte interativo na aba de importação e exige o campo `input_legenda` específico do Markdown.
3. `WidgetEditorMapas._acao_substituir_imagem` e `WidgetEditorImagens._acao_substituir_imagem`: abrem um `QFileDialog.getOpenFileName` cru, sem pré-visualização, sem recorte, sem galeria de imagens do croqui e, no caso de mapas, sem atualizar `largura_mapa` / `altura_mapa` nem oferecer reajuste proporcional dos POIs. Além disso, os cartões de mapas no Editor de Dados (`WidgetCardMapa` e nó `MAPA` no `WidgetEditorDados`) não oferecem um botão `"Substituir Imagem..."`.
4. `WidgetCampoImagem` (`editor/views/widget_campo_imagem.py` para `caminho_thumbnail` e `caminho_imagem_capa`): ainda abre `QFileDialog` + `DialogoNomeImagem` e executa `self.model.definir_imagem_memoria(...)` diretamente na View antes de emitir `imagem_alterada`, sobrescrevendo os bytes anteriores antes do `CroquiController.alterar_campo_imagem` ler `bytes_antigos` em campos de nome fixo (`thumbnail.webp`).

## Goals / Non-Goals

**Goals:**
- Unificar todos os pontos de entrada e substituição de imagens em uma arquitetura de wizard de 2 abas (`"Importar Nova Imagem"` com recorte interativo + `"Imagens do Croqui"` com galeria em disco e RAM).
- Permitir substituir a imagem de um mapa diretamente no Editor de Dados (`WidgetCardMapa` e visão de nó `MAPA` no `WidgetEditorDados`) e no Editor de Mapas (`WidgetEditorMapas`).
- Atualizar atomicamente `largura_mapa` e `altura_mapa` ao substituir a imagem de um mapa e oferecer reajuste proporcional opcional das coordenadas e dimensões de todos os POIs (`circulo`, `quadrado`, `retangulo`, `poligono` e `linha.conteudo.nos`) via biblioteca pura (`editor/core/geometrias_poi.py`) e `CmdMacro`.
- Corrigir a pureza MVC em `WidgetCampoImagem`, eliminando `DialogoNomeImagem` e a mutação direta do `CroquiModel` na View.

**Non-Goals:**
- Não alterar o formato de persistência no disco (`imagens/*.webp` em WebP lossy Q85) nem os limites de orçamento de megapixels ($4.0\text{ MP}$ padrão e $1.0\text{ MP}$ para capas e escaladas).
- Não introduzir novos tipos de comandos fora dos 7 comandos canônicos de `editor/commands/comandos_protobuf.py`.

## Decisions

### 1. Arquitetura Unificada do Wizard de Imagens (2 Abas + Recorte + Modos de Operação)
- **Decisão**: Consolidar os componentes visuais compartilhados (`AreaDropImagem`, barra de recorte interativo, painel de metadados e grade de galeria `"Imagens do Croqui"` alimentada por `listar_imagens_disponiveis_croqui`) de modo que `DialogoAdicionarMapa` (usado para adição/substituição de mapas, campos de imagem e editor de imagens) e `DialogoInserirImagemMarkdown` compartilhem a mesma experiência de 2 abas com recorte interativo:
  - **Aba 0 (`"Importar Nova Imagem"`)**: Botão `"Selecionar Imagem..."`, `AreaDropImagem` com seleção retangular (*rubber-band*), barra de recorte (`✂ Recortar Área Selecionada` e `↺ Reverter Imagem Original`), painel de metadados (`lbl_dimensoes`, `lbl_tamanho`) e campo de nome `.webp`.
  - **Aba 1 (`"Imagens do Croqui"`)**: Campo de busca em tempo real (`input_busca`), `QListWidget` em modo `IconMode` exibindo miniaturas tanto de `pasta_imagens` no disco quanto de `imagens_em_memoria` na RAM, e rótulo de metadados da imagem selecionada.
- **Modos de Operação em `DialogoAdicionarMapa`**:
  - **Modo Adição / Nome Livre** (`caminho_destino_fixo=None`): permite editar o nome `.webp` na aba de importação (validando colisão contra disco e RAM) ou escolher uma imagem existente na aba `"Imagens do Croqui"` (que reutiliza o `imagens/<nome>.webp` selecionado sem duplicar arquivo).
  - **Modo Substituição de Arquivo Fixo** (`caminho_destino_fixo="thumbnail.webp"`): trava o campo `input_nome` com o nome fixo na aba de importação (sem acusar colisão consigo mesmo) e, caso o usuário selecione outra imagem na aba `"Imagens do Croqui"` ou importe uma nova imagem, disponibiliza os bytes processados para gravar sob o destino ou atualizar a referência conforme o contexto.
  - **Modo Substituição de Mapa** (`modo_substituicao_mapa=True`, recebendo `largura_antiga`, `altura_antiga`, `qtd_pois` e `caminho_atual`): exibe um `QCheckBox` (`chk_reescalar_pois`: *"Reajustar proporcionalmente os N Pontos de Interesse (POIs) para a nova resolução"*) sempre que `qtd_pois > 0` e a resolução da imagem escolhida $(W_{\text{novo}}, H_{\text{novo}})$ diferir de $(W_{\text{antigo}}, H_{\text{antigo}})$, marcado por padrão (`True`).
- **Alternativas consideradas**: Criar um terceiro diálogo separado apenas para substituição. Descartado porque geraria triplicação de código de UI com `DialogoAdicionarMapa` e `DialogoInserirImagemMarkdown`.

### 2. Reajuste Proporcional Puro de POIs em `editor/core/geometrias_poi.py`
- **Decisão**: Implementar a função pura `redimensionar_pois_proporcionalmente(pontos_de_interesse, largura_antiga, altura_antiga, largura_nova, altura_nova) -> list[Mapa.PontoDeInteresse]` em `editor/core/geometrias_poi.py`.
- **Regras Matemáticas de Escala**:
  - Se `largura_antiga <= 0` ou `altura_antiga <= 0` ou `largura_nova <= 0` ou `altura_nova <= 0`, ou se `(largura_antiga, altura_antiga) == (largura_nova, altura_nova)`, retorna cópias inalteradas dos POIs.
  - Fatores de escala: $s_x = W_{\text{novo}} / W_{\text{antigo}}$, $s_y = H_{\text{novo}} / H_{\text{antigo}}$ e escala isotrópica $s_{\text{iso}} = \sqrt{s_x \cdot s_y}$.
  - Para cada `PontoDeInteresse`, cria uma cópia (`CopyFrom`) e ajusta o `oneof tipo_area` ativo:
    - `circulo`: `x = round(x * s_x)`, `y = round(y * s_y)`, `raio = max(1, round(raio * s_iso))`.
    - `quadrado`: `x = round(x * s_x)`, `y = round(y * s_y)`, `lado = max(1, round(lado * s_iso))`.
    - `retangulo`: `x = round(x * s_x)`, `y = round(y * s_y)`, `comprimento = max(1, round(comprimento * s_x))`, `largura = max(1, round(largura * s_y))` (mantendo `angulo_graus_x100`).
    - `poligono`: para cada par $(x_i, y_i)$ em `coordenadas`, atualiza para `round(x_i * s_x)` e `round(y_i * s_y)`.
    - `linha`: para cada `no` em `linha.conteudo.nos`, atualiza `no.x = round(no.x * s_x)` e `no.y = round(no.y * s_y)`.
- **Por quê**: Sendo uma função pura sobre mensagens Protobuf em `editor/core/geometrias_poi.py`, é 100% testável de forma isolada sem instanciar interface gráfica e pode ser reutilizada tanto pelo `CroquiController` quanto pelo `MapasController`.

### 3. Substituição Atômica de Imagem de Mapa nos Controladores via `CmdMacro`
- **Decisão**: Adicionar `substituir_imagem_mapa` em `CroquiController` (recebendo `caminho_mapa: str`, ex.: `"setores.0.conteudo.mapas.0"`) e delegar a partir de `MapasController.substituir_imagem_mapa(mapa, ...)`, construindo um único `CmdMacro` composto exclusivamente pelos comandos canônicos:
  1. `CmdAlterarImagem(model, nome_arquivo_novo, bytes_antigos, bytes_novos)` (quando houver novos bytes importados/recortados ou quando o buffer precisar ser atualizado).
  2. `CmdAlterarCampo(model, f"{caminho_mapa}.caminho_imagem_mapa", caminho_relativo_antigo, caminho_relativo_novo)` (se o caminho relativo mudou).
  3. `CmdAlterarCampo(model, f"{caminho_mapa}.largura_mapa", largura_antiga, largura_nova)` e `CmdAlterarCampo(model, f"{caminho_mapa}.altura_mapa", altura_antiga, altura_nova)` (se as dimensões mudaram).
  4. Se `reescalar_pois=True` e as dimensões mudaram: um `CmdAlterarCampo(model, f"{caminho_mapa}.pontos_de_interesse.{idx}", poi_antigo_copia, poi_novo)` para cada POI do mapa.
- **Por quê**: Respeita rigorosamente o limite dos 7 comandos canônicos (`editor/arquitetura_mvc_test.py`) e garante que um único `Ctrl+Z` (`Undo`) reverta simultaneamente os bytes da imagem, o caminho do arquivo, a largura/altura do mapa e todas as coordenadas dos POIs.

### 4. Correção de Pureza MVC em `WidgetCampoImagem`
- **Decisão**: Remover `self.model.definir_imagem_memoria(caminho_relativo, bytes_conteudo)` de `WidgetCampoImagem.aplicar_nova_imagem` e remover a classe `DialogoNomeImagem`. Quando o usuário confirmar a troca de imagem no wizard unificado, `WidgetCampoImagem` apenas emitirá `imagem_alterada.emit(caminho_relativo, bytes_conteudo)`, deixando o `CroquiController.alterar_campo_imagem` capturar os `bytes_antigos` reais do modelo antes de empilhar `CmdMacro([CmdAlterarImagem, CmdAlterarCampo])`.

## Risks / Trade-offs

- **[Risco] Arredondamento cumulativo de coordenadas inteiras em múltiplos redimensionamentos sucessivos** → **Mitigação**: O checkbox de reajuste proporcional só é exibido quando há diferença real de resolução ($W_{\text{novo}} \times H_{\text{novo}} \neq W_{\text{antigo}} \times H_{\text{antigo}}$) e o comando `CmdAlterarCampo` armazena o `PontoDeInteresse` original completo antes da escala, permitindo que o `Undo` restaure as coordenadas originais exatas sem perda de precisão.
- **[Risco] Testes existentes que interagem com `WidgetCampoImagem` ou `DialogoAdicionarMapa`** → **Mitigação**: Manter o método público `aplicar_nova_imagem(caminho_relativo, bytes_conteudo)` em `WidgetCampoImagem` e os atributos públicos de `DialogoAdicionarMapa` (`bytes_webp`, `nome_arquivo_final`, `largura`, `altura`, `caminho_imagem_relativo`, `reescalar_pois`), atualizando os testes espelhados 1:1 para exercitar os novos comportamentos pela API pública.
