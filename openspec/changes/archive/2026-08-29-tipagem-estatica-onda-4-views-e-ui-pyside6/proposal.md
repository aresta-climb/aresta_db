# Proposta: Tipagem Estática Estrita - Onda 4: Views e UI PySide6

## Why

A camada de interface gráfica (`editor/views/`, `editor/legacy_views/` e `editor/models/`) concentra grande parte das interações de usuário, widgets customizados, delegates, adaptadores de árvore e renderizadores de croquis/mapas. Por ser historicamente dinâmica, essa camada representava uma das maiores fontes de bugs em tempo de execução (ex: divergências de assinaturas em slots do PySide6, passagem de tipos incorretos em factories de widgets e chamadas a métodos inexistentes). A aplicação de tipagem estática estrita sob o modo `strict = true` do MyPy elimina esses erros em tempo de compilação/análise estática e garante estabilidade para a interface desktop.

## What Changes

- **Modelos Remanescentes**: Concluir a anotação com tipagem estática estrita de `editor/models/croqui_model.py` e `editor/models/compilacao_log.py`.
- **Views Principais e Estilos**: Anotar com tipagem estática estrita `editor/views/estilo.py`, `editor/views/notificacao.py`, `editor/views/publish_dialog.py`, `editor/views/tela_de_abertura.py` e `editor/views/dialogo_recuperacao_sessao.py`.
- **Widgets de Edição e Árvores**: Anotar `editor/views/tree_view_adapter.py`, `editor/views/protobuf_widget_factory.py`, `editor/views/widget_campo_coordenada_e7.py`, `editor/views/widget_campo_imagem.py`, `editor/views/widget_editor_dados.py`, `editor/views/widget_editor_mapas.py`, `editor/views/widget_mensagem_coordenada.py`, `editor/views/widget_painel_referencias.py` e `editor/views/widget_saida_compilacao.py`.
- **Diálogos de Criação e Edição**: Anotar `editor/views/dialogos/dialogo_adicionar_mapa.py`, `dialogo_busca_referencia.py`, `dialogo_criar_botao.py`, `dialogo_criar_escalada.py`, `dialogo_criar_pico.py`, `dialogo_criar_setor_ou_grupo.py`, `dialogo_inserir_imagem_markdown.py` e `dialogo_perfil_autor.py`.
- **Views Legadas e Ponto de Entrada**: Anotar `editor/legacy_views/` (`dialogo_busca_croqui.py`, `dialogo_conexao_celular.py`, `widget_editor_imagens.py`, `tela_de_carregamento.py`, `area_principal.py`) e `editor/main.py`.
- **Guardião e Metateste AST**: Expandir `tests/tipagem_estatica_test.py` para incluir todos os módulos da Onda 4, garantindo 100% de conformidade com MyPy estrito e anotações AST completas.

## Capabilities

### New Capabilities
- `tipagem-estatica-views-ui`: Define os requisitos e cenários de tipagem estática estrita para toda a camada de interface gráfica PySide6, widgets, diálogos e ponto de entrada da aplicação.

### Modified Capabilities
<!-- Nenhuma mudança em requisitos funcionais existentes -->

## Impact

- **Código Afetado**: `editor/models/`, `editor/views/`, `editor/views/dialogos/`, `editor/legacy_views/`, `editor/main.py` e `tests/tipagem_estatica_test.py`.
- **Dependências**: PySide6, PIL, Protobuf, MyPy.
- **Breaking Changes**: Nenhuma quebra funcional ou de API externa; mudanças restritas a anotações de tipo e correções defensivas.
