## Why

Atualmente, o editor de formulários do Aresta exibe campos numéricos e de texto de forma genérica:
1. **Coordenadas geográficas E7**: No Protobuf, as coordenadas são representadas como inteiros no padrão E7 (`sint32`, multiplicadas por $10^7$, ex: `-198980280`), o que resulta em campos de `QSpinBox` com inteiros ilegíveis, difíceis de digitar e sem distinção clara dos hemisférios (N/S e E/W), além de dificultar a colagem direta de dados de serviços como Google Maps.
2. **Campos de imagem**: Campos como `caminho_thumbnail` do croqui e `caminho_imagem_mapa` são exibidos como caixas de texto simples (`QLineEdit`), sem exibir a pré-visualização da imagem, metadados (dimensões e tamanho de arquivo) nem fornecer um fluxo facilitado de substituição com pré-processamento/compressão em WebP e integração com a aba do Editor de Imagens.

Esta mudança introduz formatos visuais especializados (`CampoFormatoUi`) para coordenadas E7 e imagens, adotando bibliotecas isoladas e testáveis de acordo com os princípios de engenharia do repositório.

## What Changes

- **Extensões de Schema Protobuf (`croqui.proto`)**:
  - Novos valores no enum `CampoFormatoUi`: `LATITUDE_E7`, `LONGITUDE_E7` e `IMAGEM`.
  - Nova opção de campo `string nome_arquivo_imagem = 50009;` para declarar nomes fixos de arquivo de destino (ex: `thumbnail.webp`).
  - Anotação dos campos `Coordenada.latitude` com `LATITUDE_E7`, `Coordenada.longitude` com `LONGITUDE_E7` e `Croqui.caminho_thumbnail` com `IMAGEM` e `nome_arquivo_imagem = "thumbnail.webp"`.
- **Biblioteca Isolada de Coordenadas (`editor/core/coordenadas.py`)**:
  - Funções puras para conversão bidirecional de inteiro E7 para ponto flutuante com 7 casas decimais.
  - Parser robusto para colagem inteligente de coordenadas (identificando pares numéricos decimais, graus/minutos/segundos DMS e letras cardinais N/S/E/W e L/O).
  - Formatação e identificação de hemisférios e limites geográficos.
- **Componente Visual de Coordenadas E7 (`WidgetCampoCoordenadaE7`)**:
  - Entrada de ponto flutuante com indicador visual da Rosa dos Ventos (`19.8980280° S (Sul)` e `43.5212340° W (Oeste)`).
  - Colagem inteligente com micro-diálogo de confirmação e botão de inversão rápida de eixos (Latitude/Longitude).
  - Botão de atalho para abrir a coordenada no Google Maps.
- **Biblioteca Isolada de Imagens (`editor/core/processamento_imagem_campo.py`)**:
  - Funções puras para leitura de metadados (dimensões em pixels e tamanho em KB), sanitização de nomes de arquivos e compressão/conversão WebP em disco.
- **Componente Visual de Imagens (`WidgetCampoImagem`)**:
  - Card com pré-visualização da imagem em miniatura e metadados.
  - Botão de substituição de imagem com pré-processamento automático para WebP.
  - Diálogo para definição de nome de arquivo quando o campo não possui nome fixo, com alerta de conflito para arquivos existentes.
  - Botão "Abrir no Editor de Imagens" para focar diretamente a imagem na aba de edição de imagens.
  - Sincronização automática com a lista de imagens da `PaginaImagens`.
- **Garantia de Histórico (Undo/Redo)**:
  - Todas as mutações de dados na interface ocorrem exclusivamente através da pilha de histórico via `CroquiController` e `CmdAlterarPrimitivo`.

## Capabilities

### New Capabilities
- `editor-campo-coordenada-e7`: Biblioteca de conversão e componente visual para edição de coordenadas em ponto flutuante convertidas bidirecionalmente para o padrão E7, com identificação de hemisférios, colagem inteligente e integração com Google Maps.
- `editor-campo-imagem`: Biblioteca de processamento e componente visual para manipulação de campos de imagem com miniatura, compressão automática para WebP, gestão de nomes de arquivos e navegação para o Editor de Imagens.

### Modified Capabilities

## Impact

- `aresta_api/proto/croqui.proto`: Novos enums em `CampoFormatoUi`, nova extensão de `FieldOptions` e anotações em `Coordenada` e `Croqui`.
- `editor/core/coordenadas.py` e `editor/core/coordenadas_test.py`: Nova biblioteca de utilidades e parser de coordenadas com 100% de cobertura.
- `editor/core/processamento_imagem_campo.py` e `editor/core/processamento_imagem_campo_test.py`: Nova biblioteca de processamento de imagens com 100% de cobertura.
- `editor/views/widget_campo_coordenada_e7.py` e `widget_campo_coordenada_e7_test.py`: Novo widget de UI para coordenadas E7.
- `editor/views/widget_campo_imagem.py` e `widget_campo_imagem_test.py`: Novo widget de UI para imagens.
- `editor/views/widget_editor_dados.py` e `editor/views/protobuf_widget_factory.py`: Integração com os novos widgets baseada em `formato_na_ui`.
- `editor/legacy_views/area_principal.py`: Navegação direta e foco na imagem selecionada na aba de imagens.
