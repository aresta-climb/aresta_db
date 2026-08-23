## 1. Schema Protobuf e Anotações

- [x] 1.1 Adicionar os valores `LATITUDE_E7`, `LONGITUDE_E7` e `IMAGEM` no enum `CampoFormatoUi` em `aresta_api/proto/croqui.proto`.
- [x] 1.2 Adicionar a extensão de campo `string nome_arquivo_imagem = 50009;` em `aresta_api/proto/croqui.proto`.
- [x] 1.3 Atualizar as anotações dos campos `Coordenada.latitude`, `Coordenada.longitude` e `Croqui.caminho_thumbnail` em `aresta_api/proto/croqui.proto`.
- [x] 1.4 Recompilar os arquivos Protobuf gerados para Python (`protoc`).

## 2. Biblioteca de Coordenadas (Library-First & TDD)

- [x] 2.1 Criar a suíte de testes unitários `editor/core/coordenadas_test.py` (Red) cobrindo conversão bidirecional E7/float com 7 casas decimais, validação de limites geográficos, formatação cardinal (`N/S/E/W` e `Sul/Norte/Oeste/Leste`) e parser de pares de coordenadas e DMS.
- [x] 2.2 Implementar a biblioteca pura `editor/core/coordenadas.py` (Green) até atingir 100% de cobertura nos testes unitários.

## 3. Biblioteca de Processamento de Imagens em Memória (Library-First & TDD)

- [x] 3.1 Criar a suíte de testes unitários `editor/core/processamento_imagem_campo_test.py` (Red) cobrindo leitura de metadados a partir de bytes, sanitização de nomes, verificação de conflitos e conversão/compressão WebP para bytes em RAM.
- [x] 3.2 Implementar a biblioteca pura `editor/core/processamento_imagem_campo.py` (Green) até atingir 100% de cobertura nos testes unitários.

## 4. Buffer de Imagens no Modelo e Comando de Histórico (TDD)

- [x] 4.1 Criar testes em `editor/commands/comandos_protobuf_test.py` e `editor/models/croqui_model_test.py` (Red) para o buffer `_imagens_em_memoria`, o comando `CmdAlterarCampoImagem` (Undo/Redo sem tocar no disco) e a gravação de imagens na extração para salvamento (`extrair_arquivos_e_serializar`).
- [x] 4.2 Implementar os métodos de buffer de imagens em `editor/models/croqui_model.py` e o comando `CmdAlterarCampoImagem` em `editor/commands/comandos_protobuf.py` (Green).
- [x] 4.3 Implementar a gravação física das imagens pendentes da memória para o disco no método `extrair_arquivos_e_serializar` de `CroquiModel`.

## 5. Testes de Integração em Primeiro Lugar (Princípio V)

- [x] 5.1 Criar a suíte de testes de integração `editor/views/campos_customizados_integracao_test.py` (Red) verificando os contratos de renderização, mutação via `CroquiController` (`CmdAlterarPrimitivo` e `CmdAlterarCampoImagem`), propagação de sinais, pré-visualização a partir da RAM e suporte a Undo/Redo no `WidgetEditorDados`.

## 6. Componentes Visuais (Views) & TDD

- [x] 6.1 Criar a suíte de testes `editor/views/widget_campo_coordenada_e7_test.py` (Red) cobrindo rendering, formatação, diálogo de colagem inteligente e atalho do Google Maps.
- [x] 6.2 Implementar o componente `editor/views/widget_campo_coordenada_e7.py` (Green).
- [x] 6.3 Criar a suíte de testes `editor/views/widget_campo_imagem_test.py` (Red) cobrindo exibição de miniatura a partir da RAM/disco, metadados, diálogo de seleção/conflito de nome e botão de foco no editor de imagens.
- [x] 6.4 Implementar o componente `editor/views/widget_campo_imagem.py` (Green).

## 7. Integração com o Formulário de Dados e Fábrica de Widgets

- [x] 7.1 Atualizar `editor/views/protobuf_widget_factory.py` e `editor/views/widget_editor_dados.py` para instanciar `WidgetCampoCoordenadaE7` e `WidgetCampoImagem` de acordo com `formato_na_ui`.
- [x] 7.2 Garantir que todas as alterações de coordenadas utilizem `controller.alterar_primitivo` e alterações de imagem utilizem `controller.alterar_campo_imagem` (Princípio VII).
- [x] 7.3 Atualizar os testes unitários existentes em `editor/views/widget_editor_dados_test.py` e `editor/views/protobuf_widget_factory_test.py`.

## 8. Integração com a Área Principal e Sincronização de Imagens e Mapas

- [x] 8.1 Em `editor/legacy_views/area_principal.py`, conectar a ação "Abrir no Editor" de `WidgetCampoImagem` para focar a aba `PaginaImagens` na imagem correspondente.
- [x] 8.2 Garantir que, após o salvamento (`salvar_croqui`), a `AreaPrincipal` notifique `self.pagina_imagens.carregar_imagens(caminho_db)` e `self.pagina_mapas.carregar_mapas(...)` para recarregar do disco as imagens atualizadas.
- [x] 8.3 Criar testes de integração em `editor/legacy_views/area_principal_imagens_integracao_test.py` validando o recarregamento e navegação entre a aba de dados e a aba de imagens.

## 9. Validação Final e Cobertura

- [x] 9.1 Executar a suíte completa de testes (`pytest`) e certificar 100% de cobertura nos novos módulos e nenhuma regressão nos testes existentes.
- [x] 9.2 Validar compilação do banco de dados e integridade dos arquivos gerados.
