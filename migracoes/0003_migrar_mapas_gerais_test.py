# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import sys
import yaml
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import importlib.util

spec = importlib.util.spec_from_file_location("migracao_0003", str(Path(__file__).parent / "0003_migrar_mapas_gerais.py"))
migracao_0003 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migracao_0003)

def test_migracao_0003(tmp_path):
    pico_path = tmp_path / "pico_teste"
    pico_path.mkdir()
    
    # Prepara o estado original
    croqui_data = {
        "botoes": [
            {
                "texto": "Mapas Gerais",
                "destino": {
                    "secao_textual": {
                        "caminho": "mapas_gerais.md"
                    }
                }
            },
            {
                "texto": "Outra Secao",
                "destino": {
                    "secao_textual": {
                        "caminho": "outra_secao.md"
                    }
                }
            }
        ],
        "picos": [
            {"nome": "Pico A"}
        ]
    }
    croqui_yaml_path = pico_path / "croqui.yaml"
    with open(croqui_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(croqui_data, f)
        
    md_file = pico_path / "mapas_gerais.md"
    md_content = """---
titulo: "Mapas"
---
![Acesso](imagens/mapas_gerais/p0.webp)
Algum texto extra
![Setores](imagens/mapas_gerais/p1.webp)
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    # Executa a migração
    migracao_0003.migrar(pico_path)
    
    # Verifica UP no croqui.yaml
    with open(croqui_yaml_path, "r", encoding="utf-8") as f:
        croqui_pos_up = yaml.safe_load(f)
        
    assert len(croqui_pos_up["botoes"]) == 1
    assert croqui_pos_up["botoes"][0]["destino"]["secao_textual"]["caminho"] == "outra_secao.md"
    assert "mapas_gerais" in croqui_pos_up["picos"][0]
    assert croqui_pos_up["picos"][0]["mapas_gerais"]["caminho"] == "mapas_gerais.md"
    
    # Verifica UP no mapas_gerais.md
    with open(md_file, "r", encoding="utf-8") as f:
        md_pos_up = f.read()
        
    assert "caminho_imagem_mapa: imagens/mapas_gerais/p0.webp" in md_pos_up
    assert "caminho_imagem_mapa: imagens/mapas_gerais/p1.webp" in md_pos_up
    assert "Algum texto extra" not in md_pos_up
    assert "![Acesso]" not in md_pos_up

def test_extrair_imagens_do_markdown():
    corpo = "Texto inicial\n\n![Mapa 1](imagens/mapa1.webp)\n\nTexto no meio\n![Mapa 2](imagens/mapa2.png)\nFim"
    imagens = migracao_0003.extrair_imagens_do_markdown(corpo)
    assert imagens == ["imagens/mapa1.webp", "imagens/mapa2.png"]

def test_extrair_imagens_vazio():
    assert migracao_0003.extrair_imagens_do_markdown("Texto sem imagens") == []

def test_converter_md_texto_para_mapas_sem_mapas_anteriores():
    frontmatter = {"titulo": "Mapas Gerais"}
    corpo = "![Mapa](imagens/mapa1.webp)"
    
    novo_frontmatter, novo_corpo = migracao_0003.converter_md_texto_para_mapas(frontmatter, corpo)
    
    assert novo_frontmatter["titulo"] == "Mapas Gerais"
    assert len(novo_frontmatter["mapas"]) == 1
    assert novo_frontmatter["mapas"][0]["caminho_imagem_mapa"] == "imagens/mapa1.webp"
    assert novo_corpo == corpo

def test_converter_md_texto_para_mapas_com_mapas_existentes():
    frontmatter = {
        "mapas": [
            {"caminho_imagem_mapa": "imagens/mapa1.webp"}
        ]
    }
    corpo = "![Mapa 1](imagens/mapa1.webp)\n![Mapa 2](imagens/mapa2.webp)"
    
    novo_frontmatter, novo_corpo = migracao_0003.converter_md_texto_para_mapas(frontmatter, corpo)
    
    assert len(novo_frontmatter["mapas"]) == 2
    assert novo_frontmatter["mapas"][0]["caminho_imagem_mapa"] == "imagens/mapa1.webp"
    assert novo_frontmatter["mapas"][1]["caminho_imagem_mapa"] == "imagens/mapa2.webp"

