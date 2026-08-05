# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import sys
import yaml
from pathlib import Path
import importlib.util

sys.path.append(str(Path(__file__).resolve().parent.parent))

spec = importlib.util.spec_from_file_location("migracao_0004", str(Path(__file__).parent / "0004_padronizar_geometrias_poi.py"))
migracao_0004 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migracao_0004)
migrar = migracao_0004.migrar

def test_migracao_0004_padroniza_geometrias(tmp_path):
    pico_path = tmp_path / "br_teste"
    pico_path.mkdir()
    
    md_content = '''---
mapas:
- caminho_imagem_mapa: imagens/mapa1.webp
  largura_mapa: 1000
  altura_mapa: 1000
  pontos_de_interesse:
  - id: '1'
    label: Via 1
    circular:
      x: 10
      y: 10
      raio: 5
  - id: '2'
    label: Via 2
    box:
      x: 20
      y: 20
      comprimento: 10
      largura: 10
  - id: '3'
    label: Via 3
    area_livre:
      coordenadas: [0, 0, 10, 0, 10, 10]
---
# Texto
'''
    
    md_file = pico_path / "mapa.md"
    md_file.write_text(md_content, encoding="utf-8")
    
    migrar(pico_path)
    
    novo_conteudo = md_file.read_text(encoding="utf-8")
    
    assert "circular:" not in novo_conteudo
    assert "box:" not in novo_conteudo
    assert "area_livre:" not in novo_conteudo
    
    assert "circulo:" in novo_conteudo
    assert "retangulo:" in novo_conteudo
    assert "poligono:" in novo_conteudo
    
    # Valida estrutura via YAML
    frontmatter_str = novo_conteudo.split("---")[1]
    parsed = yaml.safe_load(frontmatter_str)
    
    pois = parsed["mapas"][0]["pontos_de_interesse"]
    assert "circulo" in pois[0]
    assert "retangulo" in pois[1]
    assert "poligono" in pois[2]
