# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import sys
from pathlib import Path

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
            {
                "id": "1",
                "label": "Via Teste",
                "retangulo": {"x": 50, "y": 50, "comprimento": 50, "largura": 50},
            }
        ],
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
    assert poi1["retangulo"]["x"] == 50
    assert poi1["retangulo"]["y"] == 50


def test_finalizacao_error_on_legacy_format(tmp_path):
    pico_path = tmp_path / "pico_erro"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)

    md_file = pico_path / "setor.md"
    md_file.write_text(
        "---\nmapas:\n- caminho_imagem_mapa: imagens/mapa.webp\n---\n", encoding="utf-8"
    )

    json_data = {
        "arquivo_md": "setor.md",
        "caminho_imagem_mapa": "imagens/mapa.webp",
        "dimensoes_mapa": {"largura": 500, "altura": 500},
        "pontos_de_interesse": [
            {"id": "old", "box": {"xmin": 10, "ymin": 10, "xmax": 20, "ymax": 20}}
        ],
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


def test_finalizacao_mapas_gerais(tmp_path):
    pico_path = tmp_path / "pico_teste"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)

    # Cria o arquivo mapas_gerais.md
    md_file = pico_path / "mapas_gerais.md"
    md_content = """---
mapas:
- caminho_imagem_mapa: imagens/mapas_gerais/p0.webp
---
"""
    md_file.write_text(md_content, encoding="utf-8")

    # Cria a imagem falsa
    img_dir = pico_path / "imagens" / "mapas_gerais"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_file = img_dir / "p0.webp"
    img_file.write_bytes(b"fake_image_data")

    # Cria o arquivo JSON do mapa
    json_data = {
        "arquivo_md": "mapas_gerais.md",
        "caminho_imagem_mapa": "imagens/mapas_gerais/p0.webp",
        "dimensoes_imagem": {"largura": 1024, "altura": 768},
        "pontos_de_interesse": [
            {
                "id": "Setor_A",
                "label": "Setor A",
                "retangulo": {"x": 100, "y": 100, "comprimento": 50, "largura": 50},
            }
        ],
    }
    json_file = raw_mapas_dir / "p0.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    finalizar_mapas(str(pico_path))

    frontmatter, _ = parse_md_com_frontmatter(str(md_file))
    assert frontmatter["mapas"][0]["largura_mapa"] == 1024
    assert frontmatter["mapas"][0]["altura_mapa"] == 768

    poi1 = frontmatter["mapas"][0]["pontos_de_interesse"][0]
    assert poi1["id"] == "Setor_A"
    assert poi1["retangulo"]["x"] == 100


def test_finalizacao_mapas_em_escaladas(tmp_path):
    pico_path = tmp_path / "pico_esc"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)

    md_file = pico_path / "setor_bloco.md"
    md_content = """---
nome: Bloco Central
escaladas:
- boulder:
    nome: Boulder Alpha
  mapas:
  - caminho_imagem_mapa: imagens/mapa_boulder.webp
---
Corpo do bloco.
"""
    md_file.write_text(md_content, encoding="utf-8")

    img_dir = pico_path / "imagens"
    img_dir.mkdir(exist_ok=True)
    (img_dir / "mapa_boulder.webp").write_bytes(b"fake_image_data")

    json_data = {
        "arquivo_md": "setor_bloco.md",
        "caminho_imagem_mapa": "imagens/mapa_boulder.webp",
        "dimensoes_imagem": {"largura": 600, "altura": 400},
        "pertence_a_escalada": True,
        "escalada_nome": "Boulder Alpha",
        "escalada_indice": 0,
        "pontos_de_interesse": [
            {"id": "start", "label": "Start", "circulo": {"x": 20, "y": 30, "raio": 15}}
        ],
    }
    json_file = raw_mapas_dir / "mapa_boulder.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    finalizar_mapas(str(pico_path))

    frontmatter, _ = parse_md_com_frontmatter(str(md_file))
    esc = frontmatter["escaladas"][0]
    assert "mapas" in esc
    assert esc["mapas"][0]["largura_mapa"] == 600
    assert esc["mapas"][0]["altura_mapa"] == 400

    poi = esc["mapas"][0]["pontos_de_interesse"][0]
    assert poi["id"] == "start"
    assert poi.get("rotulo") == "Start" or poi.get("label") == "Start"
    assert poi["circulo"]["x"] == 20


def test_finalizacao_mapas_injeta_uids_e_padroniza_rotulo(tmp_path):
    """Garante que finalizar_mapas gera UIDs NanoID 14c para POIs novos e padroniza label -> rotulo."""
    from scripts.gerenciar_uids_lib import gerar_uid, validar_uid

    pico_path = tmp_path / "pico_uids"
    raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
    raw_mapas_dir.mkdir(parents=True)

    md_file = pico_path / "setor_uids.md"
    md_content = """---
nome: Setor UIDs
mapas:
- caminho_imagem_mapa: imagens/mapa.webp
---
Corpo do arquivo.
"""
    md_file.write_text(md_content, encoding="utf-8")

    img_dir = pico_path / "imagens"
    img_dir.mkdir(exist_ok=True)
    (img_dir / "mapa.webp").write_bytes(b"dummy")

    uid_existente = gerar_uid()
    json_data = {
        "arquivo_md": "setor_uids.md",
        "caminho_imagem_mapa": "imagens/mapa.webp",
        "dimensoes_imagem": {"largura": 800, "altura": 600},
        "pontos_de_interesse": [
            {"id": "1", "label": "Via 1", "circulo": {"x": 100, "y": 150, "raio": 20}},
            {
                "id": "2",
                "uid": uid_existente,
                "rotulo": "Via 2",
                "quadrado": {"x": 200, "y": 250, "lado": 30},
            },
        ],
    }
    json_file = raw_mapas_dir / "mapa.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    finalizar_mapas(str(pico_path))

    frontmatter, _ = parse_md_com_frontmatter(str(md_file))
    pois = frontmatter["mapas"][0]["pontos_de_interesse"]
    assert len(pois) == 2

    # Primeiro POI (era sem UID e com label)
    assert validar_uid(pois[0].get("uid"))
    assert pois[0].get("rotulo") == "Via 1"
    assert "label" not in pois[0]

    # Segundo POI (já tinha UID e rotulo)
    assert pois[1].get("uid") == uid_existente
    assert pois[1].get("rotulo") == "Via 2"
    assert "label" not in pois[1]


def test_parse_md_com_yaml_invalido(tmp_path):
    md_file = tmp_path / "invalido.md"
    md_file.write_text("---\n: invalido: yaml: [}\n---\nCorpo", encoding="utf-8")
    fm, corpo = parse_md_com_frontmatter(str(md_file))
    assert fm == {}
    assert corpo == "Corpo"


def test_finalizar_mapas_validacoes_diretorios(tmp_path, capsys):
    # Diretório não existe
    finalizar_mapas(tmp_path / "inexistente")
    out = capsys.readouterr().out
    assert "não foi encontrado" in out

    # Diretório sem pasta raw_mapas
    pico = tmp_path / "pico_vazio"
    pico.mkdir()
    finalizar_mapas(pico)
    out = capsys.readouterr().out
    assert "Diretório não existe" in out

    # Pasta raw_mapas vazia
    raw_dir = pico / "imagens" / "raw_mapas"
    raw_dir.mkdir(parents=True)
    finalizar_mapas(pico)
    out = capsys.readouterr().out
    assert "Nenhum arquivo JSON para processar" in out


def test_finalizar_mapas_erros_json_e_md(tmp_path, capsys):
    pico = tmp_path / "pico_erros"
    raw_dir = pico / "imagens" / "raw_mapas"
    raw_dir.mkdir(parents=True)

    # 1. JSON corrompido
    (raw_dir / "corrompido.json").write_text("{invalido json", encoding="utf-8")

    # 2. JSON faltando campos
    (raw_dir / "incompleto.json").write_text(
        json.dumps({"arquivo_md": "teste.md"}), encoding="utf-8"
    )

    # 3. MD não existe
    (raw_dir / "md_inexistente.json").write_text(
        json.dumps({"arquivo_md": "inexistente.md", "caminho_imagem_mapa": "img.webp"}),
        encoding="utf-8",
    )

    # 4. MD sem frontmatter
    (pico / "sem_fm.md").write_text("Apenas texto puro", encoding="utf-8")
    (raw_dir / "sem_fm.json").write_text(
        json.dumps({"arquivo_md": "sem_fm.md", "caminho_imagem_mapa": "img.webp"}), encoding="utf-8"
    )

    finalizar_mapas(pico)
    out = capsys.readouterr().out
    assert "Erro ao ler corrompido.json" in out
    assert "JSON incompleto incompleto.json" in out
    assert "Arquivo Markdown de origem não encontrado" in out
    assert "Não foi possível carregar frontmatter" in out


def test_finalizar_mapas_formatos_geometria_e_avisos(tmp_path, capsys):
    pico = tmp_path / "pico_geom"
    raw_dir = pico / "imagens" / "raw_mapas"
    raw_dir.mkdir(parents=True)

    md_file = pico / "setor.md"
    md_file.write_text(
        """---
mapas:
- caminho_imagem_mapa: imagens/mapa.webp
---
""",
        encoding="utf-8",
    )

    json_data = {
        "arquivo_md": "setor.md",
        "caminho_imagem_mapa": "imagens/mapa.webp",
        "dimensoes_imagem": {"largura": 400, "altura": 300},
        "pontos_de_interesse": [
            # 1. circular legado
            {"id": "c1", "rotulo": "Circ", "circular": {"x": 10, "y": 10, "raio": 5}},
            # 2. box com angulo legado
            {
                "id": "b1",
                "rotulo": "Box",
                "box": {"x": 20, "y": 20, "comprimento": 30, "largura": 15, "angulo": 45.0},
            },
            # 3. poligono e linha
            {"id": "p1", "rotulo": "Poli", "poligono": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]},
            {"id": "l1", "rotulo": "Linha", "linha": [{"x": 1, "y": 1}, {"x": 2, "y": 2}]},
            # 4. quadrado incompleto
            {"id": "q_bad", "rotulo": "QBad", "quadrado": {"x": 5}},
            # 5. retangulo incompleto
            {"id": "r_bad", "rotulo": "RBad", "retangulo": {"x": 5}},
            # 6. tipo desconhecido
            {"id": "desc", "rotulo": "Desc", "outro": 123},
        ],
    }
    (raw_dir / "mapa.json").write_text(json.dumps(json_data), encoding="utf-8")

    finalizar_mapas(pico)
    out = capsys.readouterr().out
    assert "está incompleto e será ignorado" in out
    assert "tem formato desconhecido e será ignorado" in out

    fm, _ = parse_md_com_frontmatter(str(md_file))
    pois = fm["mapas"][0]["pontos_de_interesse"]
    assert len(pois) == 4
    assert "circulo" in pois[0]
    assert "retangulo" in pois[1]
    assert pois[1]["retangulo"]["angulo_graus_x100"] == 4500
    assert "poligono" in pois[2]
    assert "linha" in pois[3]


def test_finalizar_mapas_via_multiplas_enfiadas_e_mapa_ausente(tmp_path, capsys):
    pico = tmp_path / "pico_multi"
    raw_dir = pico / "imagens" / "raw_mapas"
    raw_dir.mkdir(parents=True)

    md_file = pico / "setor.md"
    md_file.write_text(
        """---
escaladas:
- "escalada_invalida_nao_dict"
- via_multiplas_enfiadas:
    nome: Via Longa
    mapas:
    - caminho_imagem_mapa: imagens/mapa_multi.webp
---
""",
        encoding="utf-8",
    )

    json_data = {
        "arquivo_md": "setor.md",
        "caminho_imagem_mapa": "imagens/mapa_multi.webp",
        "dimensoes_imagem": {"largura": 500, "altura": 500},
        "pontos_de_interesse": [
            {"id": "e1", "rotulo": "E1", "circulo": {"x": 5, "y": 5, "raio": 2}}
        ],
    }
    (raw_dir / "mapa_multi.json").write_text(json.dumps(json_data), encoding="utf-8")

    # JSON de mapa que não está no markdown
    json_nao_encontrado = {
        "arquivo_md": "setor.md",
        "caminho_imagem_mapa": "imagens/nao_existe.webp",
        "dimensoes_imagem": {"largura": 500, "altura": 500},
        "pontos_de_interesse": [],
    }
    (raw_dir / "mapa_fantasma.json").write_text(json.dumps(json_nao_encontrado), encoding="utf-8")

    finalizar_mapas(pico)
    out = capsys.readouterr().out
    assert "não foi encontrado na lista 'mapas' de setor.md" in out

    fm, _ = parse_md_com_frontmatter(str(md_file))
    via = fm["escaladas"][1]["via_multiplas_enfiadas"]
    assert len(via["mapas"][0]["pontos_de_interesse"]) == 1


def test_finalizar_mapas_main_cli(tmp_path, monkeypatch, capsys):
    import runpy

    pico = tmp_path / "pico_cli"
    raw_dir = pico / "imagens" / "raw_mapas"
    raw_dir.mkdir(parents=True)

    caminho_script = Path(__file__).resolve().parent / "finalizar_mapas.py"
    monkeypatch.setattr("sys.argv", ["finalizar_mapas.py", str(pico)])
    runpy.run_path(str(caminho_script), run_name="__main__")
    out = capsys.readouterr().out
    assert "Nenhum arquivo JSON para processar" in out
