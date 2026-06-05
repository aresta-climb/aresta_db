# Especificação Técnica: Pipeline de Processamento e Compressão de Ortofotos (MBTiles + WebP)

## 1. Visão Geral
Este documento define o fluxo de trabalho (pipeline) para a criação, compressão e distribuição de mapas offline baseados em aerofotogrametria proprietária (drones). O objetivo é gerar arquivos `.mbtiles` de altíssima resolução que respeitem o limite de armazenamento de provedores gratuitos (como o limite de 100MB por arquivo do GitHub Pages) utilizando a compressão `WebP`.

## 2. Requisitos de Arquitetura
* **Captura:** Drone sub-250g (ex: DJI Mini 5 Pro).
* **Processamento:** WebODM ou Agisoft Metashape.
* **Ferramentas CLI:** GDAL (Geospatial Data Abstraction Library) via QGIS.
* **Motor de Renderização:** `flutter_map` (Dart/Flutter) com decodificação nativa via Skia/Impeller.
* **Armazenamento Local:** Sistema de arquivos do dispositivo.

## 3. Pipeline de Geração de Mapa

### Passo 1: Captura em Campo (Nadir)
* **Sobreposição (Overlap):** Mínimo de 75% frontal e 70% lateral para áreas com vegetação densa.
* **Altitude:** ~100 metros em relação à base, visando um GSD (Ground Sample Distance) de 2.5 a 3 cm/pixel.

### Passo 2: Geração do GeoTIFF
O lote de imagens (JPG/DNG) é processado no software de fotogrametria para gerar uma única ortofoto georreferenciada.
* **Output esperado:** Arquivo `.tif` (GeoTIFF).

### Passo 3: Conversão e Compressão para MBTiles (WebP)
O arquivo `.tif` gerado costuma ser massivo (Gigabytes). A conversão direta para o banco de dados SQLite (`.mbtiles`) com injeção do formato `WebP` é feita via linha de comando utilizando o **GDAL**.

No terminal, execute:
```bash
gdal_translate -of MBTILES -co TILE_FORMAT=WEBP -co QUALITY=80 mapa_setor_input.tif mapa_setor_output.mbtiles
```
* **`TILE_FORMAT=WEBP`**: Força o GDAL a gravar o BLOB do SQLite utilizando o encoder WebP em vez do PNG/JPG padrão da especificação 1.3.
* **`QUALITY=80`**: Define o nível de compressão com perdas (lossy). O valor 80 oferece o melhor balanço entre preservação de texturas rochosas e redução drástica de tamanho (redução estimada de 60% a 80% em relação ao PNG).

### Passo 4: Otimização de Área (Recorte por Buffer de GPX)
Se a área mapeada exceder o limite de 100MB mesmo em WebP, o recorte baseado nas trilhas deve ser aplicado no QGIS antes da execução do GDAL:
1. Importar o GPX das trilhas de aproximação no QGIS.
2. Criar um Buffer (ex: 30 metros) ao redor do traçado geométrico.
3. Recortar (Clip) a camada raster (`.tif`) usando a máscara do buffer.
4. Exportar o novo `.tif` focado e rodar o `gdal_translate`.

## 4. Script Alternativo: Migração de MBTiles Legados (Python)
Caso existam arquivos `.mbtiles` gerados previamente em JPG ou PNG, o script Python abaixo deve ser executado para reescrever a coluna `tile_data` para WebP e limpar o banco de dados.

**Dependências:** `pip install Pillow`

```python
import sqlite3
import io
from PIL import Image

def optimize_mbtiles_to_webp(db_path, quality=80):
    print(f"Otimizando {db_path} para WebP...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Busca todos os tiles
    cursor.execute("SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles")
    rows = cursor.fetchall()
    
    total = len(rows)
    for i, (zoom, col, row, data) in enumerate(rows):
        # Abre o binário em memória
        img = Image.open(io.BytesIO(data))
        out_io = io.BytesIO()
        
        # Salva o binário em formato WebP
        img.save(out_io, format='WEBP', quality=quality)
        new_data = out_io.getvalue()
        
        # Atualiza a linha no SQLite
        cursor.execute(
            "UPDATE tiles SET tile_data = ? WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
            (new_data, zoom, col, row)
        )
        
        if i % 500 == 0:
            print(f"Processado {i}/{total} tiles...")
            conn.commit()
            
    conn.commit()
    
    # Executa o VACUUM para limpar espaços em branco deixados pelas imagens maiores e reduzir o tamanho físico do arquivo
    print("Executando VACUUM no banco de dados...")
    cursor.execute("VACUUM")
    conn.close()
    
    print("Otimização concluída com sucesso!")

# Exemplo de uso
# optimize_mbtiles_to_webp("meu_mapa_legado.mbtiles", quality=80)
```

## 5. Implementação no Flutter
Como o motor Skia/Impeller do Flutter suporta WebP nativamente, o pacote `flutter_map` fará a leitura do BLOB sem a necessidade de processadores customizados.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:flutter_map_mbtiles/flutter_map_mbtiles.dart';
import 'package:mbtiles/mbtiles.dart';

class OfflineDroneMap extends StatefulWidget {
  final String mbtilesPath; // Caminho no FileSystem do aparelho

  OfflineDroneMap({required this.mbtilesPath});

  @override
  _OfflineDroneMapState createState() => _OfflineDroneMapState();
}

class _OfflineDroneMapState extends State<OfflineDroneMap> {
  late Future<MbTiles> _mbtilesFuture;

  @override
  void initState() {
    super.initState();
    _mbtilesFuture = _loadMbTiles();
  }

  Future<MbTiles> _loadMbTiles() async {
    return MbTiles(mbtilesPath: widget.mbtilesPath);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MbTiles>(
      future: _mbtilesFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) return const CircularProgressIndicator();

        final mbtiles = snapshot.data!;
        final metadata = mbtiles.getMetadata();

        return FlutterMap(
          options: MapOptions(
            initialCenter: metadata.defaultCenter ?? const LatLng(-20.3683, -43.5066),
            initialZoom: metadata.defaultZoom ?? 16.0,
            maxZoom: 22.0, // Permite oversampling na UI
          ),
          children: [
            TileLayer(
              // flutter_map_mbtiles lida com a injeção do BLOB (WebP) diretamente
              tileProvider: MbTilesTileProvider(mbtiles: mbtiles),
              maxNativeZoom: 19.0, // Limite real dos dados gerados pelo drone
            ),
          ],
        );
      },
    );
  }
}
```