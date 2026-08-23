## Why

Atualmente, o editor de formulários do Aresta exibe campos numéricos e de texto de forma genérica:
1. **Coordenadas geográficas E7**: No Protobuf, as coordenadas são representadas como inteiros no padrão E7 (`sint32`, multiplicadas por $10^7$, ex: `-198980280`), o que resulta em campos de `QSpinBox` com inteiros ilegíveis, difíceis de digitar e sem distinção clara dos hemisférios (N/S e E/W), além de dificultar a colagem direta de dados de serviços como Google Maps.
2. **Campos de imagem**: Campos como `caminho_thumbnail` do croqui e `caminho_imagem_mapa` são exibidos como caixas de texto simples (`QLineEdit`), sem exibir a pré-visualização da imagem, metadados (dimensões e tamanho de arquivo) nem fornecer um fluxo facilitado de substituição com pré-processamento/compressão em WebP. Além disso, operações com imagens atualmente arriscam causar efeitos colaterais no disco antes do salvamento deliberado pelo usuário.

Esta mudança introduz formatos visuais especializados (`CampoFormatoUi`) para coordenadas E7 e imagens, acompanhados de uma arquitetura robusta de **buffer de imagens em memória RAM** com comando de histórico dedicado (`QUndoCommand`), garantindo zero efeitos colaterais no disco antes do salvamento e suporte determinístico a desfazer/refazer (Undo/Redo).

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
  - Funções puras para leitura de metadados em memória/disco (dimensões em pixels e tamanho em KB), sanitização de nomes de arquivos e compressão/conversão WebP para bytes em RAM.
- **Buffer de Imagens em Memória no `CroquiModel` e Comando de Histórico**:
  - `CroquiModel` armazena os bytes das imagens modificadas/novas em memória (`_imagens_em_memoria`), sem tocar no disco durante a edição.
  - Criação do comando `CmdAlterarCampoImagem` (`QUndoCommand`) para gerenciar as alterações de caminho e buffers de bytes em memória, garantindo Undo/Redo instantâneo e livre de erros.
  - Na ação "Salvar" (`salvar_croqui`), os bytes acumulados na RAM são gravados atomicamente no disco em `database/<croqui>/imagens/`, atualizando a `PaginaImagens` e a `PaginaMapas`.
- **Componente Visual de Imagens (`WidgetCampoImagem`)**:
  - Card com pré-visualização da imagem em miniatura a partir da RAM ou disco com metadados.
  - Botão de substituição de imagem com pré-processamento automático para WebP em memória.
  - Diálogo para definição de nome de arquivo quando o campo não possui nome fixo, com alerta de conflito para arquivos existentes.
  - Botão "Abrir no Editor de Imagens" para focar diretamente a imagem na aba de edição de imagens.

## Capabilities

### New Capabilities
- `editor-campo-coordenada-e7`: Biblioteca de conversão e componente visual para edição de coordenadas em ponto flutuante convertidas bidirecionalmente para o padrão E7, com identificação de hemisférios, colagem inteligente e integração com Google Maps.
- `editor-campo-imagem`: Biblioteca de processamento, gerenciamento de buffer de imagens em RAM no modelo e componente visual para manipulação de campos de imagem com miniatura, compressão WebP em memória, persistência atômica no salvamento e navegação para o Editor de Imagens e Mapas.

### Modified Capabilities

## Impact

- `aresta_api/proto/croqui.proto`: Novos enums em `CampoFormatoUi`, nova extensão de `FieldOptions` e anotações em `Coordenada` e `Croqui`.
- `editor/core/coordenadas.py` e `editor/core/coordenadas_test.py`: Nova biblioteca de utilidades e parser de coordenadas com 100% de cobertura.
- `editor/core/processamento_imagem_campo.py` e `editor/core/processamento_imagem_campo_test.py`: Nova biblioteca de processamento de imagens em memória com 100% de cobertura.
- `editor/models/croqui_model.py` e `editor/models/croqui_model_test.py`: Gerenciamento do buffer `_imagens_em_memoria` e gravação em disco no salvamento.
- `editor/commands/comandos_protobuf.py` e `editor/commands/comandos_protobuf_test.py`: Comando `CmdAlterarCampoImagem`.
- `editor/views/widget_campo_coordenada_e7.py` e `widget_campo_coordenada_e7_test.py`: Novo widget de UI para coordenadas E7.
- `editor/views/widget_campo_imagem.py` e `widget_campo_imagem_test.py`: Novo widget de UI para imagens.
- `editor/views/widget_editor_dados.py` e `editor/views/protobuf_widget_factory.py`: Integração com os novos widgets baseada em `formato_na_ui`.
- `editor/legacy_views/area_principal.py`: Navegação direta para imagem selecionada e recarregamento da `PaginaImagens` e `PaginaMapas` no salvamento.
