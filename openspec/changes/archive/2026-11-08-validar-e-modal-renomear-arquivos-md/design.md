# Design

## Context

Conforme descrito em `proposal.md`, a edição livre do nome de arquivo `.md` (`ext_metadados_arquivo.caminho_novo`) através de um `QLineEdit` comum em `WidgetEditorDados._render_filename_field` permitiu que entradas com caracteres especiais de sistema de arquivos (`:`, `"`, `*`, `|`, `>`, `<`, `/`, `\`) chegassem até `persistir_contexto_memoria_no_disco` (`scripts/deploy_generated.py`) e `escrever_texto_se_modificado` (`editor/core/serializacao_util.py`), causando `OSError` no Windows (issues #86 e #87). Adicionalmente, os fallbacks de geração automática de nome de arquivo em `CroquiModel.extrair_arquivos_e_serializar` usavam apenas `.replace(' ', '_').lower()` sem remover acentos ou símbolos ilegais.

## Goals / Non-Goals

**Goals:**
- Seguir integralmente os 8 princípios do `AGENTS.md`: tudo em português brasileiro, arquitetura *Library-First*, TDD (*Red-Green-Refactor*) com espelhamento 1:1 (`_test.py`), 100% de cobertura comportamental sem mocks para código interno e mutações de estado exclusivamente via `QUndoCommand`.
- Introduzir `CampoFormatoUi.NOME_ARQUIVO = 9` em `aresta_api/proto/croqui.proto` e anotar `MetadadosArquivoNoEditor.caminho_novo`.
- Centralizar a validação, normalização e truncamento (`<= 100` caracteres) de nomes de arquivos `.md` em `editor/core/nomes_arquivos.py`.
- Tornar a visualização do nome de arquivo no formulário de dados somente-leitura (`WidgetCampoNomeArquivo`), delegando qualquer renomeação ao modal `DialogoRenomearArquivo` acionado pelo botão `"Modificar..."`.
- Unificar a validação com recusa (botão desabilitado + mensagem de erro) em `DialogoRenomearArquivo`, `DialogoCriarBotao` e `DialogoCriarSetorOuGrupo`.
- Garantir que `CroquiModel.extrair_arquivos_e_serializar` sempre produza nomes de arquivo `.md` válidos e sanitizados mesmo quando `caminho_novo` estiver ausente ou o título da entidade contiver apenas símbolos.

**Non-Goals:**
- Não renomear arquivos `.md` existentes em `database/` que já possuem menos de `100` caracteres (o maior arquivo atual em `database/` possui `59` caracteres).
- Não alterar o formato de persistência do Shadow State (`MetadadosArquivoNoEditor`) nem o contrato de compilação binária (`compilado.binarypb`).

## Decisions

### 1. Novo Enum `CampoFormatoUi.NOME_ARQUIVO` e Descritor em `MetadadosArquivoNoEditor`
- **Decisão**: Adicionar `NOME_ARQUIVO = 9` em `CampoFormatoUi.Enum` (`aresta_api/proto/croqui.proto`) e anotar `MetadadosArquivoNoEditor`:
  ```protobuf
  message MetadadosArquivoNoEditor {
    string caminho_original = 1 [(aresta.formato_na_ui) = INVISIVEL];
    string caminho_novo = 2 [
      (aresta.formato_na_ui) = NOME_ARQUIVO,
      (aresta.texto_na_ui) = "Nome do arquivo"
    ];
    string dados_json_originais = 4 [(aresta.formato_na_ui) = INVISIVEL];
    reserved 3;
  }
  ```
  Em `ProtobufWidgetFactory.create_widget`, quando `formato == croqui_pb2.CampoFormatoUi.NOME_ARQUIVO`, retornar uma instância de `WidgetCampoNomeArquivo`.
- **Racional**: Alinha a renderização de nomes de arquivos de metadados ao mesmo mecanismo declarativo usado por `LATITUDE_E7`, `LONGITUDE_E7` e `IMAGEM`.
- **Alternativas consideradas**: Criar o widget manualmente apenas dentro de `_render_filename_field` sem atualizar o `.proto`. Rejeitado porque o usuário definiu que o metadado de arquivo deve ser guiado pelo enum `CampoFormatoUi` no Protobuf.

### 2. Biblioteca Pura de Validação e Normalização em `editor/core/nomes_arquivos.py`
- **Decisão**: Expandir `editor/core/nomes_arquivos.py` com funções puras:
  - `LIMITE_MAXIMO_CARACTERES_ARQUIVO_MD: int = 100`
  - `normalizar_entrada_nome_arquivo_md(texto: str) -> str`: faz `.strip()`, converte espaços em branco (`\s+`) para `_` e adiciona `.md` ao final caso não esteja vazio e ainda não termine em `.md` (preservando demais caracteres para que o validador possa acusar erro caso o usuário digite caracteres ilegais como `:`, `/`, `<`, acentos ou maiúsculas).
  - `validar_nome_arquivo_md(texto: str, arquivos_existentes: Sequence[str] = (), arquivo_atual: str = "") -> tuple[bool, str, str]`:
    Retorna `(valido, nome_normalizado, mensagem_erro)`:
    1. Se `texto.strip()` estiver vazio ou for apenas `".md"`: retorna `(False, "", "O nome do arquivo não pode ficar vazio.")`.
    2. Normaliza espaços para `_` e garante sufixo `.md`.
    3. Se `len(nome_normalizado) > 100`: retorna `(False, nome_normalizado, "O nome do arquivo deve ter no máximo 100 caracteres.")`.
    4. Verifica se o tronco (sem `.md`) casa com `^[a-z0-9]+(_[a-z0-9]+)*$`: se não casar, retorna `(False, nome_normalizado, "Nome inválido: use apenas letras minúsculas sem acento, números e '_'.")`.
    5. Se `nome_normalizado.lower()` estiver em `arquivos_existentes` (e for diferente de `arquivo_atual.lower()`): retorna `(False, nome_normalizado, f"Já existe um arquivo com o nome '{nome_normalizado}'.")`.
    6. Caso contrário, retorna `(True, nome_normalizado, "")`.
  - `garantir_nome_arquivo_md_seguro(caminho_proposto: str | None, nome_entidade: str | None, prefixo_padrao: str) -> str`:
    Usado como barreira final no `CroquiModel.extrair_arquivos_e_serializar`. Se `caminho_proposto` for válido pelo padrão `^[a-z0-9]+(_[a-z0-9]+)*\.md$` e `<= 100` chars, mantém; caso contrário, gera a partir de `deduplicar_prefixo(nome_entidade, prefixo_padrao)` truncando o tronco em `97` caracteres (`100 - len(".md")`).
- **Racional**: Isola 100% das regras de negócio em funções puras Python sem dependência de Qt (Princípio II - *Library-First*), permitindo testes unitários exaustivos e garantindo que tanto os 3 modais da UI quanto o `CroquiModel` compartilhem a mesma verdade.

### 3. `WidgetCampoNomeArquivo` Somente-Leitura + `DialogoRenomearArquivo`
- **Decisão**:
  ```text
  +-----------------------------------------------------------------------+
  | WidgetCampoNomeArquivo                                                |
  | [ QLineEdit (readOnly=True, property="__filename__") ] [ Modificar ]  |
  +-----------------------------------------------------------------------+
                                                                 |
                                                                 v
  +-----------------------------------------------------------------------+
  | DialogoRenomearArquivo (QDialog modal)                                |
  | - QLineEdit inicializado com o nome atual                             |
  | - Ao digitar, converte espacos em '_' e chama validar_nome_arquivo_md |
  | - Se invalido: exibe erro em lbl_aviso e desabilita btn_confirmar     |
  | - Se valido e confirmado: emite sinal nome_alterado(novo_nome)        |
  +-----------------------------------------------------------------------+
  ```
  - O `QLineEdit` interno de `WidgetCampoNomeArquivo` mantém `setProperty("protobuf_field", "__filename__")` e `setReadOnly(True)`.
  - Como `readOnly=True`, a ação `editar_campo_linha` do Robô Caótico (que filtra `not w.isReadOnly()`) ignora a edição direta inline, evitando mutações sem validação.
  - Quando o modal `DialogoRenomearArquivo` é aceito, o `WidgetEditorDados` invoca `self.controller.alterar_metadados_caminho_novo(wrapper_msg, ext_desc, old_val, novo_nome)`, registrando o comando na pilha `QUndoStack` (Princípio VIII).
  - Em `AtualizadorUi.atualizar_widgets_para_mensagem`, quando `campo_nome == "ext_metadados_arquivo"`, atualiza o valor exibido em `WidgetCampoNomeArquivo` (via `definir_nome_arquivo` / ` edit_nome.setText`).

## Risks / Trade-offs

- **[Risk] Testes existentes que buscavam o `QLineEdit` com `protobuf_field == "__filename__"` e simulavam `editingFinished.emit()` direto nele** → **Mitigation**: Manter o `QLineEdit` somente-leitura dentro de `WidgetCampoNomeArquivo` com `property("protobuf_field", "__filename__")` para inspeção de leitura, e atualizar os testes que testavam a mutação pela UI para exercitar a confirmação via `DialogoRenomearArquivo` / `WidgetCampoNomeArquivo`.
- **[Risk] Arquivos existentes em `database/` com caracteres acentuados (`setor_forno_da_onça.md` e `setor_parede_do_ladrão.md` em `br_mg_caete_monte_alvao`)** → **Mitigation**: Em `garantir_nome_arquivo_md_seguro`, preservar `caminho_original` já existente em disco se não houve tentativa de renomeação inválida, ou permitir a leitura sem quebrar croquis legados, aplicando a validação estrita em novas criações, renomeações e quando `caminho_novo` contiver caracteres ilegais de sistema de arquivos (`<>:"/\|?*` ou controle).
