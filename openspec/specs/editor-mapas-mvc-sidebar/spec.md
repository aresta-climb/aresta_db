# editor-mapas-mvc-sidebar Specification

## Purpose
TBD - created by archiving change migrar-editor-mapas-mvc.

## Requirements

### Requirement: Sidebar alimentada pelo modelo
A sidebar do WidgetEditorMapas MUST exibir uma lista interativa de todos os mapas disponíveis extraídos da árvore de mensagens correntes (`CroquiModel`), e não varrendo o disco por arquivos markdown.

#### Scenario: Atualizar contexto de mapas disponíveis
- **WHEN** o `CroquiModel` é carregado no editor de mapas
- **THEN** a barra lateral esvazia a lista anterior e renderiza itens correspondentes a cada mensagem Protobuf que define um `Mapa` no croqui, listando-os pelo seu título.
