# Especificação Técnica: Mapeamento Aéreo de Varredura (120m) e Corridor Mapping

## 1. Visão Geral
Este documento define o protocolo de aerofotogrametria simplificada para o aplicativo Antigravity. A estratégia centraliza a captura de imagens de contexto geográfico e trilhas de aproximação na altitude máxima legal de **120 metros**, garantindo uma resolução de ~3,5 cm/px (Zoom 22). O uso de altitudes inferiores fica estritamente reservado para o mapeamento oblíquo/vertical das faces rochosas.

## 2. Parâmetros Base da Captura (120 metros)
A decisão de padronizar o voo topográfico em 120 metros baseia-se na física óptica do sensor do VANT (ex: DJI Mini 5 Pro):
* **Resolução (GSD):** 3,5 cm/pixel (Suficiente para identificar trilhas, clareiras e pedras médias).
* **Pegada Visual (Footprint):** Cada foto captura uma área de aproximadamente **160m x 120m** no solo.
* **Sobreposição (Overlap):** 75% Frontal e 70% Lateral (mantido para garantir *tie points* em áreas de dossel florestal denso).
* **Eficiência:** Cobertura de até 50 hectares por bateria.

## 3. Protocolos Operacionais de Voo

A execução no campo divide-se em duas abordagens, dependendo da extensão do setor:

### 3.1. Abordagem A: Setores Compactos (Ex: Lapinha, Ouroboulder, Baú - 40 a 60 ha)
* **Geometria de Voo:** Polígono / Grid Simples.
* **Execução:** O drone decola do centro do setor, sobe a 120 metros e varre a área total.
* **Vantagem:** Cobre a rocha, a vegetação e o acesso curto em cerca de 20 minutos (1 bateria).

### 3.2. Abordagem B: Setores de Longa Aproximação (Ex: Pedra Grande - > 100 ha)
* **Geometria de Voo:** Corridor Mapping híbrido (Linha + Polígono).
* **Execução (Fase 1 - Trilha):** Importação do `.gpx` da trilha no Dronelink. O drone voa a 120m em linha reta seguindo o eixo da trilha. Como a largura da foto é de 160m, uma única passada em linha reta cobre a trilha e 80m de margem de cada lado, eliminando a necessidade de zigue-zague.
* **Execução (Fase 2 - Base):** Ao chegar no polígono da montanha, o plano transiciona para um grid quadrado de 120m cobrindo os 50 hectares da área principal.
* **Vantagem:** Evita o mapeamento inútil de quilômetros quadrados de mata distante da trilha. Operação viabilizada via revezamento de recarga veicular (12V) durante a missão.

## 4. Exceção Operacional: Faces Rochosas (Croqui Vertical)
O voo Nadir (câmera a -90°) a 50 metros está abolido do protocolo de trilhas devido ao bloqueio visual por copas de árvores.
Para mapear a rocha para o desenho dos croquis e visualização de agarras/chapeletas:
* **Protocolo:** Grid Vertical (câmera entre 0° e -20°).
* **Distância:** 30 a 40 metros de afastamento da parede.
* **Processamento:** Projeto isolado, não mesclado com o mapa topográfico de 120m.

## 5. Pipeline de Processamento e Renderização

### 5.1. Fotogrametria (Workstation)
O processamento em hardware de alto desempenho (arquitetura multithread, 32GB+ RAM, SSD NVMe Gen 4, GPU CUDA) é drasticamente acelerado por esta arquitetura:
* Lote único de imagens (sem necessidade de calibração cruzada de múltiplas altitudes).
* Redução de 80% na contagem total de imagens em comparação ao protocolo de 50 metros.
* Geração do GeoTIFF (`.tif`) em tempo otimizado.

### 5.2. Empacotamento MBTiles (GDAL)
A exportação final para o contêiner SQLite do aplicativo deve ser capada cirurgicamente para evitar explosão de armazenamento:

```bash
gdal_translate -of MBTILES -co TILE_FORMAT=WEBP -co QUALITY=80 -outsize 100% 100% -a_srs EPSG:3857 mapa_120m_input.tif mapa_otimizado_output.mbtiles
```
* **Limite de Zoom Físico:** O GDAL exportará tiles apenas até o **Zoom 22**, que reflete o limite real dos dados (3,5 cm/px).
* **Tamanho do Arquivo:** A combinação de *Corridor Mapping*, cap de Zoom 22 e compressão WebP (Quality 80) garante que mapas de complexos inteiros fiquem abaixo do limite de 100MB de provedores de CDN gratuitos.

### 5.3. Engine do Aplicativo (Flutter)
A renderização no aplicativo `flutter_map` delega os níveis de zoom mais profundos ao motor gráfico:
```dart
TileLayer(
  tileProvider: MbTilesTileProvider(mbtiles: mbtiles),
  maxNativeZoom: 22.0, // Limite real físico no SQLite
  maxZoom: 25.0,       // Zoom digital esticado dinamicamente pelo Flutter
)
```