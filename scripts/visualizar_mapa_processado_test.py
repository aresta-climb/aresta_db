# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import json
from pathlib import Path
from PIL import Image
import pytest
from unittest.mock import patch

from scripts.visualizar_mapa_processado import processar_mapa, main


def test_processar_mapa_fluxo_completo(tmp_path):
    caminho_img = tmp_path / "mapa.png"
    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    img.save(caminho_img)

    dados_json = {
        "dimensoes_mapa": {
            "canto_superior_esquerdo": {"x": 10, "y": 10},
            "largura": 150,
            "altura": 150,
        },
        "pontos_de_interesse": [
            {"tipo": "circulo", "coordenadas": [30, 30], "propriedades": {"raio": 10}},
            {"tipo": "quadrado", "coordenadas": [60, 60], "propriedades": {"lado": 20}},
            {"tipo": "retangulo", "coordenadas": [100, 100], "propriedades": {"comprimento": 30, "largura": 15, "angulo_graus_x100": 4500}},
            {"tipo": "poligono", "coordenadas": [10, 10, 20, 10, 20, 20, 10, 20]},
            {"tipo": "invalido"},
        ],
    }
    caminho_json = tmp_path / "mapa.json"
    caminho_json.write_text(json.dumps(dados_json), encoding="utf-8")

    processar_mapa(str(caminho_img), str(caminho_json))

    caminho_saida = tmp_path / "mapa_processado.webp"
    assert caminho_saida.exists()


def test_processar_mapa_arquivos_inexistentes(tmp_path, capsys):
    caminho_img = tmp_path / "inexistente.png"
    caminho_json = tmp_path / "inexistente.json"

    processar_mapa(str(caminho_img), str(caminho_json))
    out, _ = capsys.readouterr()
    assert "não encontrada" in out

    caminho_img_real = tmp_path / "mapa_real.png"
    Image.new("RGB", (50, 50)).save(caminho_img_real)
    processar_mapa(str(caminho_img_real), str(caminho_json))
    out, _ = capsys.readouterr()
    assert "não encontrado" in out


def test_main_cli(tmp_path):
    caminho_img = tmp_path / "mapa.png"
    Image.new("RGB", (50, 50)).save(caminho_img)
    caminho_json = tmp_path / "mapa.json"
    caminho_json.write_text(json.dumps({"pontos_de_interesse": []}), encoding="utf-8")

    with patch("sys.argv", ["visualizar_mapa_processado.py", "--imagem", str(caminho_img), "--pontos_json", str(caminho_json)]):
        main()

    assert (tmp_path / "mapa_processado.webp").exists()
