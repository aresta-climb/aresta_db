# Proposal

## Why

As issues [#86](https://github.com/aresta-climb/aresta_db/issues/86) (`ARESTA-EDITOR-1C`) e [#87](https://github.com/aresta-climb/aresta_db/issues/87) (`ARESTA-EDITOR-1D`) demonstraram que a edição livre do campo `Nome do arquivo:` (`ext_metadados_arquivo.caminho_novo`) diretamente no formulário de dados permite injetar caracteres ilegais de sistema de arquivos (`:`, `"`, `*`, `|`, `<`, `>`, `/`, `\`) ou strings vazias, resultando em crashes fatais (`OSError: [Errno 22]` e `OSError: [WinError 123]`) durante o salvamento e compilação do croqui. Além disso, os diálogos de criação de entidades e os fallbacks automáticos do `CroquiModel` não impõem validação estrita de formato e comprimento (`<= 100` caracteres em `snake_case`), permitindo nomes de arquivos malformados no banco de dados.

## What Changes

- **Novo formato de UI no Protobuf (`CampoFormatoUi.NOME_ARQUIVO`)**:
  - Adicionar o valor `NOME_ARQUIVO = 9` ao `enum` `CampoFormatoUi` em `aresta_api/proto/croqui.proto`.
  - Anotar o campo `MetadadosArquivoNoEditor.caminho_novo` com `[(aresta.formato_na_ui) = NOME_ARQUIVO, (aresta.texto_na_ui) = "Nome do arquivo"]` e marcar `caminho_original` e `dados_json_originais` com `[(aresta.formato_na_ui) = INVISIVEL]`.
- **Biblioteca de Validação e Normalização de Nomes de Arquivo Markdown (`editor/core/nomes_arquivos.py`)**:
  - Criar funções puras para normalizar espaços em `_` e validar nomes de arquivos `.md` exigindo formato estrito `^[a-z0-9]+(_[a-z0-9]+)*\.md$`, comprimento total máximo de `100` caracteres (`<= 100`), não-vacuidade e ausência de colisão com outros arquivos `.md` do croqui.
  - Substituir os fallbacks legados `.replace(' ', '_').lower()` em `CroquiModel.extrair_arquivos_e_serializar` pela geração sanitizada via `para_snake_case` / `gerar_nome_arquivo_entidade`, garantindo fallback seguro mesmo quando o título da entidade contiver apenas símbolos.
- **Novo Componente `WidgetCampoNomeArquivo` e Modal `DialogoRenomearArquivo`**:
  - Substituir o `QLineEdit` editável inline de `_render_filename_field` por `WidgetCampoNomeArquivo` (instanciado via `ProtobufWidgetFactory` para `CampoFormatoUi.NOME_ARQUIVO`), exibindo o nome atual em um `QLineEdit` somente-leitura (`readOnly=True`) acompanhado do botão `"Modificar..."`.
  - Ao clicar em `"Modificar..."`, abrir o modal `DialogoRenomearArquivo`, que converte espaços em `_` automaticamente e **recusa a confirmação** (desabilitando o botão de confirmar e exibindo mensagem explicativa em `lbl_aviso`) enquanto o nome for vazio, contiver caracteres inválidos, exceder `100` caracteres ou duplicar outro arquivo do croqui.
  - Aplicar a mesma regra de validação e recusa nos diálogos `DialogoCriarBotao` e `DialogoCriarSetorOuGrupo`.
- **Suíte de Regressão do Robô Caótico**:
  - Incorporar as receitas das issues #86 e #87 em `editor/caos/caminhos_regressao/` para verificação contínua em `editor/caos/regressao_caminhos_test.py`.

## Capabilities

### New Capabilities
- `editor-campo-nome-arquivo`: Componente visual somente-leitura com botão de modificação (`WidgetCampoNomeArquivo`), diálogo modal de renomeação (`DialogoRenomearArquivo`) e regras unificadas de validação e sanitização de nomes de arquivos `.md` (`<= 100` caracteres, `snake_case` ASCII estrito e verificação de unicidade).

### Modified Capabilities
- `editor-dados-formularios`: Atualiza o requisito `Edição de Arquivos Externos e Nome de Arquivo na UI` para substituir a edição direta inline por exibição somente-leitura com acionamento de modal validado (`CampoFormatoUi.NOME_ARQUIVO`) e geração automática sanitizada no `CroquiModel`.

## Impact

- **Protobuf (`aresta_api`)**: `aresta_api/proto/croqui.proto` e stubs compilados em `aresta_api/proto/generated/`.
- **Core & Model**: `editor/core/nomes_arquivos.py`, `editor/models/croqui_model.py`.
- **Views & Diálogos**: `editor/views/protobuf_widget_factory.py`, `editor/views/widget_editor_dados.py`, `editor/views/widget_campo_nome_arquivo.py`, `editor/views/dialogos/dialogo_renomear_arquivo.py`, `editor/views/dialogos/dialogo_criar_botao.py`, `editor/views/dialogos/dialogo_criar_setor_ou_grupo.py`.
- **Testes e Caos**: Espelhamento 1:1 de testes unitários e de integração (`*_test.py`) e receitas de regressão em `editor/caos/caminhos_regressao/`.
