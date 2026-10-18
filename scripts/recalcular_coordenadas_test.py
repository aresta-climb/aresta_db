# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes comportamentais para o utilitário de recálculo de coordenadas de POIs."""

import json
from pathlib import Path

from PIL import Image

from scripts.markdown_frontmatter_lib import parse_md_com_frontmatter
from scripts.recalcular_coordenadas import (
    escalar_valor,
    processar_poi,
    recalcular_coordenadas,
)


def test_escalar_valor_e_processar_poi_todas_geometrias() -> None:
    """Garante o redimensionamento proporcional em círculos, retângulos, linhas e polígonos."""
    assert escalar_valor(None, 2.0) is None
    assert escalar_valor(10, 1.5) == 15

    poi = {
        "circular": {"x": 10, "y": 20, "raio": 4},
        "circulo": {"x": 100, "y": 200, "raio": 10},
        "retangulo": {"x": 50, "y": 60, "largura": 30, "altura": 40},
        "linha": {"pontos": [{"x": 5, "y": 10}, {"x": 15, "y": 20}]},
        "poligono": {"pontos": [{"x": 2, "y": 4}]},
    }
    processar_poi(poi, 2.0, 3.0)

    assert poi["circular"] == {"x": 20, "y": 60, "raio": 10}
    assert poi["circulo"] == {"x": 200, "y": 600, "raio": 25}
    assert poi["retangulo"] == {"x": 100, "y": 180, "largura": 60, "altura": 120}
    assert poi["linha"]["pontos"] == [{"x": 10, "y": 30}, {"x": 30, "y": 60}]
    assert poi["poligono"]["pontos"] == [{"x": 4, "y": 12}]


def test_recalcular_coordenadas_atualiza_json_e_markdown_com_libyaml(tmp_path: Path) -> None:
    """Garante atualização de coordenadas em JSONs e Markdowns via parse/salvar frontmatter unificado."""
    db_path = tmp_path / "croqui_recalculo"
    imagens_dir = db_path / "imagens"
    raw_mapas_dir = imagens_dir / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)

    # Cria uma imagem WebP real de 400x300
    Image.new("RGB", (400, 300), color="white").save(imagens_dir / "mapa1.webp", format="WEBP")

    # 1. JSON que deve ser atualizado (200x150 -> 400x300, escala 2x)
    (raw_mapas_dir / "mapa1.json").write_text(
        json.dumps(
            {
                "caminho_imagem_mapa": "imagens/mapa1.webp",
                "dimensoes_imagem": {"largura": 200, "altura": 150},
                "pontos_de_interesse": [{"circulo": {"x": 10, "y": 20, "raio": 5}}],
            }
        ),
        encoding="utf-8",
    )
    # JSONs que devem ser ignorados (ocr_result, sem caminho, imagem inexistente, dim=0, diff<=2px)
    (raw_mapas_dir / "ignorar.ocr_result.json").write_text("{}", encoding="utf-8")
    (raw_mapas_dir / "sem_caminho.json").write_text("{}", encoding="utf-8")
    (raw_mapas_dir / "img_inexistente.json").write_text(
        json.dumps({"caminho_imagem_mapa": "imagens/inexistente.webp"}), encoding="utf-8"
    )
    (raw_mapas_dir / "dim_zero.json").write_text(
        json.dumps(
            {
                "caminho_imagem_mapa": "imagens/mapa1.webp",
                "dimensoes_imagem": {"largura": 0, "altura": 150},
            }
        ),
        encoding="utf-8",
    )
    (raw_mapas_dir / "quase_igual.json").write_text(
        json.dumps(
            {
                "caminho_imagem_mapa": "imagens/mapa1.webp",
                "dimensoes_imagem": {"largura": 399, "altura": 299},
            }
        ),
        encoding="utf-8",
    )

    # 2. Markdowns
    (db_path / "sem_frontmatter.md").write_text("Apenas texto", encoding="utf-8")
    (db_path / "sem_mapas.md").write_text("---\nnome: Sem Mapas\n---\nCorpo", encoding="utf-8")
    (db_path / "setor1.md").write_text(
        """---
nome: Setor 1
mapas:
  - caminho_imagem_mapa: ""
  - caminho_imagem_mapa: imagens/inexistente.webp
    largura_mapa: 100
    altura_mapa: 100
  - caminho_imagem_mapa: imagens/mapa1.webp
    largura_mapa: 0
    altura_mapa: 150
  - caminho_imagem_mapa: imagens/mapa1.webp
    largura_mapa: 400
    altura_mapa: 300
  - caminho_imagem_mapa: imagens/mapa1.webp
    largura_mapa: 200
    altura_mapa: 150
    pontos_de_interesse:
      - rotulo: '01'
        circulo:
          x: 25
          y: 30
          raio: 6
---
Corpo do setor.
""",
        encoding="utf-8",
    )

    json_mod, md_mod = recalcular_coordenadas(db_path)
    assert json_mod == 1
    assert md_mod == 1

    dados_json = json.loads((raw_mapas_dir / "mapa1.json").read_text(encoding="utf-8"))
    assert dados_json["dimensoes_imagem"] == {"largura": 400, "altura": 300}
    assert dados_json["pontos_de_interesse"][0]["circulo"] == {"x": 20, "y": 40, "raio": 10}

    fm, corpo = parse_md_com_frontmatter(db_path / "setor1.md")
    assert fm is not None
    mapa_atualizado = fm["mapas"][4]
    assert mapa_atualizado["largura_mapa"] == 400
    assert mapa_atualizado["altura_mapa"] == 300
    assert mapa_atualizado["pontos_de_interesse"][0]["circulo"] == {"x": 50, "y": 60, "raio": 12}
    assert corpo == "Corpo do setor."
