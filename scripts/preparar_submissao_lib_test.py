# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.append(str(ROOT_PATH))

from scripts.preparar_submissao_lib import (
    validar_pontos_de_interesse_recursivo,
    validar_referencias_mapa,
    compilar_croqui
)

def test_validar_circulo_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "circulo": {"x": 10, "y": 20, "raio": 5}}
        ]
    }
    # Não deve subir exceção
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_circulo_invalido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "circulo": {"x": 10, "raio": 5}} # faltando y
        ]
    }
    with pytest.raises(ValueError, match="Círculo faltando campo 'y'"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_retangulo_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "retangulo": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": 4500}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_retangulo_angulo_valido_negativo():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "retangulo": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": -4500}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_retangulo_angulo_invalido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "retangulo": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": 40000}}
        ]
    }
    with pytest.raises(ValueError, match="angulo_graus_x100 .* deve estar entre -36000 e 36000"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_quadrado_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "quadrado": {"x": 0, "y": 0, "lado": 100, "angulo_graus_x100": 4500}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_poligono_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "poligono": {"coordenadas": [0, 0, 10, 0, 10, 10, 0, 10]}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_poligono_impar():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "poligono": {"coordenadas": [0, 0, 10, 0, 10]}}
        ]
    }
    with pytest.raises(ValueError, match="número par de coordenadas"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_tipo_invalido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "box_legada": {"xmin": 0, "ymin": 0, "xmax": 10, "ymax": 10}}
        ]
    }
    with pytest.raises(ValueError, match="Tipo de área não especificado ou inválido"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_recursivo():
    obj = {
        "picos": [
            {
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "conteudo": {
                                "pontos_de_interesse": [
                                    {"id": "erro", "circulo": {"x": 10}} # Faltando campos
                                ]
                            }
                        }
                    }
                ]
            }
        ]
    }
    with pytest.raises(ValueError, match="Círculo faltando campo 'y'"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_referencias_mapa_valido():
    croqui = {
        "picos": [{
            "nome": "Pico Teste",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"referencias": [{"escalada": "Via 1", "ids": ["A"]}]}],
                        "escaladas": [{"via_esportiva": {"nome": "Via 1"}}]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert not erros

def test_validar_referencias_mapa_entidade_inexistente():
    croqui = {
        "picos": [{
            "nome": "Pico Teste",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"referencias": [
                            {"escalada": "Via Inexistente", "ids": ["A"]},
                            {"setor": "Setor Inexistente", "ids": ["B"]},
                            {"grupo": "Grupo Inexistente", "ids": ["C"]}
                        ]}],
                        "escaladas": [{"via_esportiva": {"nome": "Via 1"}}]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert len(erros) == 3
    assert any("Via Inexistente" in e for e in erros)
    assert any("Setor Inexistente" in e for e in erros)
    assert any("Grupo Inexistente" in e for e in erros)

def test_validar_referencias_mapa_id_duplicado_na_mesma_referencia():
    croqui = {
        "picos": [{
            "nome": "Pico Teste",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"referencias": [
                            {"escalada": "Via 1", "ids": ["A", "A"]},
                            {"escalada": "Via 2", "ids": ["B"]}
                        ]}],
                        "escaladas": [
                            {"via_esportiva": {"nome": "Via 1"}},
                            {"via_esportiva": {"nome": "Via 2"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("O ID 'A' está duplicado na referência 'Via 1'" in e for e in erros)

def test_validar_referencias_mapa_multiplas_enfiadas():
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"referencias": [{"escalada": "Enfiada 1", "ids": ["ENF1"]}]}],
                        "escaladas": [{
                            "via_multiplas_enfiadas": {
                                "nome": "Paredao",
                                "enfiadas": [
                                    {"via_esportiva": {"nome": "Enfiada 1"}}
                                ]
                            }
                        }]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert not erros

def test_validar_referencias_mapa_com_grupo_e_ids_disponiveis():
    pass

@patch("scripts.preparar_submissao_lib.Path")
@patch("scripts.preparar_submissao_lib.yaml.safe_load")
@patch("scripts.preparar_submissao_lib.croqui_pb2.Croqui")
@patch("scripts.preparar_submissao_lib.json_format.ParseDict")
@patch("scripts.preparar_submissao_lib.parse_md_com_frontmatter")
@patch("scripts.preparar_submissao_lib.expandir_setores_ou_grupos_recursivo")
@patch("scripts.preparar_submissao_lib.validar_referencias_mapa")
def test_compilar_croqui_emite_avisos_em_vez_de_erro(
    mock_validar, mock_expand, mock_parse, mock_json, mock_proto, mock_yaml, mock_path, capsys
):
    """Verifica se compilar_croqui emite avisos no stdout mas NÃO lança exceção em caso de IDs inválidos."""
    # Setup mocks
    mock_validar.return_value = ["Erro de ID 1", "Erro de ID 2"]
    mock_path.return_value.exists.return_value = True
    # Precisamos que o Path do arquivo croqui.yaml e do destino existam para o mock
    # compilar_croqui faz: if not pico_path.exists():
    
    mock_yaml.return_value = {"id": "test"}
    mock_expand.return_value = {"id": "test"}
    
    with patch("builtins.open", MagicMock()):
        # Chama compilar_croqui. Não deve subir ValueError.
        compilar_croqui(Path("dummy"), Path("dummy_dest"), Path("dummy_bin"))
    
    # Captura stdout
    captured = capsys.readouterr()
    
    # Verifica se a mensagem de aviso está presente
    assert "AVISO: Inconsistência nas referências de mapa:" in captured.out
    assert "Erro de ID 1" in captured.out
    assert "Erro de ID 2" in captured.out

def test_validar_referencias_mapa_ignora_se_nao_houver_referencias_em_lugar_nenhum():
    # Se não houver referências, ele nem faz a validação pesada
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "A"}]}], # POI mas sem referência
                        "escaladas": [{"via_esportiva": {"nome": "Via 1"}}]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert not erros


from scripts.preparar_submissao_lib import corrigir_database
from scripts.helpers_migracao import configurar_croqui_teste

@patch("scripts.migrador.aplicar_migracoes")
def test_corrigir_database_chama_aplicar_migracoes(mock_aplicar, tmp_path):
    yaml_content = """
    id: test_corrigir
    nome: Teste Corrigir
    """
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_content)
    
    # Executa corrigir_database
    corrigir_database(croqui_dir)
    
    # Garante que aplicar_migracoes foi chamado
    mock_aplicar.assert_called_once_with(croqui_dir)


from scripts.preparar_submissao_lib import limpar_arquivos_nao_utilizados

def test_limpar_arquivos_nao_utilizados_deleta_imagens_e_mds(tmp_path):
    # Setup de arquivos falsos no tmp_path
    pasta_img = tmp_path / "imagens"
    pasta_img.mkdir()
    
    img_usada = pasta_img / "usada.jpg"
    img_usada.write_text("dummy")
    img_orfam = pasta_img / "orfam.png"
    img_orfam.write_text("dummy")
    
    md_usado = tmp_path / "usado.md"
    md_usado.write_text("dummy")
    md_orfao = tmp_path / "orfao.md"
    md_orfao.write_text("dummy")
    
    ignorado = tmp_path / "nao_deleta.txt"
    ignorado.write_text("dummy")

    croqui_data = {
        "botoes": [
            {
                "destino": {
                    "secao_textual": {
                        "caminho": "usado.md"
                    }
                }
            }
        ],
        "caminho_thumbnail": "imagens/usada.jpg",
        "picos": []
    }
    
    limpar_arquivos_nao_utilizados(tmp_path, croqui_data)

    assert img_usada.exists(), "Imagem usada não deve ser deletada"
    assert md_usado.exists(), "MD usado não deve ser deletado"
    assert ignorado.exists(), "Arquivos com extensões ignoradas não devem ser deletados"
    assert not img_orfam.exists(), "Imagem órfã deve ser deletada"
    assert not md_orfao.exists(), "MD órfão deve ser deletado"

def test_limpar_arquivos_preserva_mapas_gerais(tmp_path):
    # Setup de arquivos falsos no tmp_path
    mapa_geral_md = tmp_path / "mapas_gerais.md"
    mapa_geral_md.write_text("dummy")
    
    # Adiciona mapas_gerais na lista de picos
    croqui_data = {
        "picos": [
            {
                "mapas_gerais": {
                    "caminho": "mapas_gerais.md"
                }
            }
        ]
    }
    
    limpar_arquivos_nao_utilizados(tmp_path, croqui_data)

    assert mapa_geral_md.exists(), "mapas_gerais.md não deve ser deletado se referenciado por um pico"

def test_compilar_croqui_faz_inline_de_mapas_gerais(tmp_path):
    import yaml
    from scripts.preparar_submissao_lib import compilar_croqui
    
    # 1. Cria a estrutura do pico fake
    pico_path = tmp_path / "br_mg_fake"
    pico_path.mkdir()
    
    # 2. Cria mapas_gerais.md
    mapas_md = pico_path / "mapas_gerais.md"
    mapas_md.write_text("---\nmapas:\n  - caminho_imagem_mapa: img1.jpg\n---\nCorpo vazio\n", encoding="utf-8")
    
    # 3. Cria croqui.yaml
    croqui_yaml = pico_path / "croqui.yaml"
    croqui_data_in = {
        "picos": [
            {
                "nome": "Fake",
                "mapas_gerais": {
                    "caminho": "mapas_gerais.md"
                }
            }
        ]
    }
    with open(croqui_yaml, "w", encoding="utf-8") as f:
        yaml.dump(croqui_data_in, f)
        
    # 4. Destinos
    dest_yaml = tmp_path / "compilado.yaml"
    dest_binarypb = tmp_path / "compilado.binarypb"
    
    # 5. Roda compilar_croqui
    compilar_croqui(pico_path, dest_yaml, dest_binarypb)
    
    # 6. Verifica o yaml compilado
    with open(dest_yaml, "r", encoding="utf-8") as f:
        compilado = yaml.safe_load(f)
        
    pico = compilado["picos"][0]
    mapas_gerais = pico["mapas_gerais"]
    assert "mapas" in mapas_gerais["conteudo"]
    assert mapas_gerais["conteudo"]["mapas"][0]["caminho_imagem_mapa"] == "img1.jpg"

def test_yaml_dump_preserva_aspas_em_strings_numericas():
    import yaml
    
    # "08" é comumente interpretado erroneamente por não ser um octal válido (octais só vão até 7).
    # O PyYAML por padrão remove as aspas de '08', o que quebra a consistência no yaml gerado.
    dados = {
        "id": "08",
        "label": "09",
        "normal": "texto",
        "octal_valido": "07"
    }
    yaml_gerado = yaml.dump(dados, sort_keys=False)
    
    # As aspas simples ou duplas devem existir no YAML dump
    assert "'08'" in yaml_gerado or '"08"' in yaml_gerado, f"YAML não preservou aspas em '08':\n{yaml_gerado}"
    assert "'09'" in yaml_gerado or '"09"' in yaml_gerado, f"YAML não preservou aspas em '09':\n{yaml_gerado}"
