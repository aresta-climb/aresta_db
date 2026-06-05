import sys
import json
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adiciona o diretório raiz ao sys.path para importações relativas seguras
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.finalizar_mapas import finalizar_mapas, parse_md_com_frontmatter

def test_finalizacao_de_mapas(tmp_path):
    pico_path = tmp_path / "pico_teste"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)
    
    # Cria o arquivo markdown
    md_file = pico_path / "setor_teste.md"
    md_content = """---
mapas:
- caminho_imagem_mapa: imagens/mapa.webp
---
Corpo do arquivo.
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    # Cria a imagem falsa
    img_dir = pico_path / "imagens"
    img_dir.mkdir(exist_ok=True)
    img_file = img_dir / "mapa.webp"
    img_file.write_bytes(b"fake_image_data")
    
    # Cria o arquivo JSON do mapa (Formato Novo)
    json_data = {
        "arquivo_md": "setor_teste.md",
        "caminho_imagem_mapa": "imagens/mapa.webp",
        "dimensoes_imagem": {"largura": 500, "altura": 500},
        "pontos_de_interesse": [
            {"id": "1", "label": "Via Teste", "box": {"x": 50, "y": 50, "comprimento": 50, "largura": 50}}
        ]
    }
    json_file = raw_mapas_dir / "mapa.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)
        
    # Roda a funcao
    finalizar_mapas(str(pico_path))
    
    # Assertions
    # 1. Verifica se o YAML no markdown foi atualizado (coordenadas idênticas, sem corte)
    frontmatter, _ = parse_md_com_frontmatter(str(md_file))
    assert frontmatter["mapas"][0]["largura_mapa"] == 500
    assert frontmatter["mapas"][0]["altura_mapa"] == 500
    
    poi1 = frontmatter["mapas"][0]["pontos_de_interesse"][0]
    assert poi1["id"] == "1"
    assert poi1["box"]["x"] == 50
    assert poi1["box"]["y"] == 50

def test_finalizacao_error_on_legacy_format(tmp_path):
    pico_path = tmp_path / "pico_erro"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)
    
    md_file = pico_path / "setor.md"
    md_file.write_text("---\nmapas:\n- caminho_imagem_mapa: imagens/mapa.webp\n---\n", encoding="utf-8")
    
    json_data = {
        "arquivo_md": "setor.md",
        "caminho_imagem_mapa": "imagens/mapa.webp",
        "dimensoes_mapa": {"largura": 500, "altura": 500},
        "pontos_de_interesse": [
            {"id": "old", "box": {"xmin": 10, "ymin": 10, "xmax": 20, "ymax": 20}}
        ]
    }
    json_file = raw_mapas_dir / "mapa.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    import pytest
    with pytest.raises(ValueError, match="Formato legado 'xmin/ymin' detectado"):
        finalizar_mapas(str(pico_path))

def test_leitura_de_md_sem_frontmatter_yaml(tmp_path):
    md_file = tmp_path / "teste.md"
    md_file.write_text("Hello World Sem Frontmatter!")
    
    frontmatter, corpo = parse_md_com_frontmatter(str(md_file))
    assert frontmatter is None
    assert corpo == "Hello World Sem Frontmatter!"
