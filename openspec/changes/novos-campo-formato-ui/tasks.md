## 1. Schema Protobuf e Anotações

- [ ] 1.1 Adicionar os valores `LATITUDE_E7`, `LONGITUDE_E7` e `IMAGEM` no enum `CampoFormatoUi` em `aresta_api/proto/croqui.proto`.
- [ ] 1.2 Adicionar a extensão de campo `string nome_arquivo_imagem = 50009;` em `aresta_api/proto/croqui.proto`.
- [ ] 1.3 Atualizar as anotações dos campos `Coordenada.latitude`, `Coordenada.longitude` e `Croqui.caminho_thumbnail` em `aresta_api/proto/croqui.proto`.
- [ ] 1.4 Recompilar os arquivos Protobuf gerados para Python (`protoc`).

## 2. Biblioteca de Coordenadas (Library-First & TDD)

- [ ] 2.1 Criar a suíte de testes unitários `editor/core/coordenadas_test.py` (Red) cobrindo conversão bidirecional E7/float com 7 casas decimais, validação de limites geográficos, formatação cardinal (`N/S/E/W` e `Sul/Norte/Oeste/Leste`) e parser de pares de coordenadas e DMS.
- [ ] 2.2 Implementar a biblioteca pura `editor/core/coordenadas.py` (Green) até atingir 100% de cobertura nos testes unitários.

## 3. Biblioteca de Processamento de Imagens (Library-First & TDD)

- [ ] 3.1 Criar a suíte de testes unitários `editor/core/processamento_imagem_campo_test.py` (Red) cobrindo leitura de metadados, sanitização de nomes, verificação de conflitos e conversão/compressão WebP com Pillow.
- [ ] 3.2 Implementar a biblioteca pura `editor/core/processamento_imagem_campo.py` (Green) até atingir 100% de cobertura nos testes unitários.

## 4. Testes de Integração em Primeiro Lugar (Princípio V)

- [ ] 4.1 Criar a suíte de testes de integração `editor/views/campos_customizados_integracao_test.py` (Red) verificando os contratos de renderização, mutação via `CroquiController` (`CmdAlterarPrimitivo`), propagação de sinais e suporte a Undo/Redo no `WidgetEditorDados`.

## 5. Componentes Visuais (Views) & TDD

- [ ] 5.1 Criar a suíte de testes `editor/views/widget_campo_coordenada_e7_test.py` (Red) cobrindo rendering, formatação, diálogo de colagem inteligente e atalho do Google Maps.
- [ ] 5.2 Implementar o componente `editor/views/widget_campo_coordenada_e7.py` (Green).
- [ ] 5.3 Criar a suíte de testes `editor/views/widget_campo_imagem_test.py` (Red) cobrindo exibição de miniatura, metadados, diálogo de seleção/conflito de nome e botão de foco no editor de imagens.
- [ ] 5.4 Implementar o componente `editor/views/widget_campo_imagem.py` (Green).

## 6. Integração com o Formulário de Dados e Fábrica de Widgets

- [ ] 6.1 Atualizar `editor/views/protobuf_widget_factory.py` e `editor/views/widget_editor_dados.py` para instanciar `WidgetCampoCoordenadaE7` e `WidgetCampoImagem` de acordo com `formato_na_ui`.
- [ ] 6.2 Garantir que todas as alterações de coordenadas e imagens utilizem `controller.alterar_primitivo` (Princípio VII).
- [ ] 6.3 Atualizar os testes unitários existentes em `editor/views/widget_editor_dados_test.py` e `editor/views/protobuf_widget_factory_test.py`.

## 7. Integração com a Área Principal e Navegação de Imagens

- [ ] 7.1 Implementar método de navegação e foco de imagem em `editor/legacy_views/area_principal.py` e `PaginaImagens`.
- [ ] 7.2 Conectar a ação "Abrir no Editor" do `WidgetCampoImagem` e garantir o recarregamento automático da lista de imagens após substituições.
- [ ] 7.3 Criar testes de integração em `editor/legacy_views/area_principal_imagens_integracao_test.py`.

## 8. Validação Final e Cobertura

- [ ] 8.1 Executar a suíte de testes completa do editor (`pytest`).
- [ ] 8.2 Validar 100% de cobertura nos módulos criados e testar a integridade de compilação e persistência do croqui.
