import pytest
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
if str(ROOT_PATH) not in sys.path:
    sys.path.append(str(ROOT_PATH))

from scripts.preparar_submissao_lib import (
    validar_pontos_de_interesse_recursivo,
    validar_referencias_mapa
)

def test_validar_circular_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "circular": {"x": 10, "y": 20, "raio": 5}}
        ]
    }
    # Não deve subir exceção
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_circular_invalido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "circular": {"x": 10, "raio": 5}} # faltando y
        ]
    }
    with pytest.raises(ValueError, match="Círculo faltando campo 'y'"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_box_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "box": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": 4500}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_box_angulo_valido_negativo():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "box": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": -4500}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_box_angulo_invalido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "box": {"x": 0, "y": 0, "comprimento": 100, "largura": 50, "angulo_graus_x100": 40000}}
        ]
    }
    with pytest.raises(ValueError, match="angulo_graus_x100 .* deve estar entre -36000 e 36000"):
        validar_pontos_de_interesse_recursivo(obj)

def test_validar_area_livre_valido():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "area_livre": {"coordenadas": [0, 0, 10, 0, 10, 10, 0, 10]}}
        ]
    }
    validar_pontos_de_interesse_recursivo(obj)

def test_validar_area_livre_impar():
    obj = {
        "pontos_de_interesse": [
            {"id": "1", "area_livre": {"coordenadas": [0, 0, 10, 0, 10]}}
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
                                    {"id": "erro", "circular": {"x": 10}} # Faltando campos
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
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "mapas": [{"pontos_de_interesse": [{"id": "A"}]}],
                        "escaladas": [{"via_esportiva": {"nome": "Via 1", "id_no_mapa": "A"}}]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert not erros

def test_validar_referencias_mapa_id_inexistente():
    croqui = {
        "id": "meu_croqui",
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "A"}]}],
                        "escaladas": [
                            {"via_esportiva": {"nome": "Via 1", "id_no_mapa": "B"}},
                            {"boulder": {"nome": "Pedra 1", "id_no_mapa_meio": "C"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("Via 1" in e for e in erros)
    assert any("id_no_mapa 'B'" in e for e in erros)
    assert any("Pedra 1" in e for e in erros)
    assert any("id_no_mapa_meio 'C'" in e for e in erros)
    assert any("* IDs de mapa disponíveis no contexto: ['A']" in e for e in erros)

def test_validar_referencias_mapa_id_duplicado():
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "A"}]}],
                        "escaladas": [
                            {"boulder": {"nome": "Pedra 1", "id_no_mapa": "A"}},
                            {"boulder": {"nome": "Pedra 2", "id_no_mapa": "A"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("A combinação de IDs de mapa (A) está duplicada e sendo usada pelas escaladas: Pedra 1, Pedra 2." in e for e in erros)

def test_validar_referencias_mapa_id_combo_permitida():
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "A"}, {"id": "B"}]}],
                        "escaladas": [
                            {"boulder": {"nome": "Pedra 1", "id_no_mapa": "A"}},
                            {"boulder": {"nome": "Pedra 2", "id_no_mapa": "A", "id_no_mapa_meio": "B"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert not erros

def test_validar_referencias_mapa_id_meio_duplicado():
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "M1"}]}],
                        "escaladas": [
                            {"via_esportiva": {"nome": "Via 1", "id_no_mapa_meio": "M1"}},
                            {"via_esportiva": {"nome": "Via 2", "id_no_mapa_meio": "M1"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("A combinação de IDs de mapa (M1) está duplicada e sendo usada pelas escaladas: Via 1, Via 2." in e for e in erros)

def test_validar_referencias_mapa_id_setor_duplicado_no_grupo():
    croqui = {
        "picos": [{
            "setores_ou_grupos": [{
                "grupo": {
                    "conteudo": {
                        "nome": "Grupo 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "S_ID"}]}],
                        "setores": [
                            {"conteudo": {"nome": "Setor A", "id_no_mapa": "S_ID"}},
                            {"conteudo": {"nome": "Setor B", "id_no_mapa": "S_ID"}}
                        ]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("O id_no_mapa 'S_ID' está duplicado e sendo usado por: Setor 'Setor A', Setor 'Setor B'." in e for e in erros)

def test_validar_referencias_mapa_id_grupo_duplicado_no_pico():
    croqui = {
        "picos": [{
            "nome": "Pico Master",
            "mapas": [{"pontos_de_interesse": [{"id": "G_ID"}]}],
            "setores_ou_grupos": [
                {"grupo": {"conteudo": {"nome": "Grupo A", "id_no_mapa": "G_ID"}}},
                {"grupo": {"conteudo": {"nome": "Grupo B", "id_no_mapa": "G_ID"}}},
                {"setor": {"conteudo": {"nome": "Setor Solto", "id_no_mapa": "G_ID"}}}
            ]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("O id_no_mapa 'G_ID' está duplicado e sendo usado por: Grupo 'Grupo A', Grupo 'Grupo B', Setor 'Setor Solto'." in e for e in erros)


def test_validar_referencias_mapa_no_grupo_valido():
    croqui = {
        "picos": [{
            "setores_ou_grupos": [{
                "grupo": {
                    "conteudo": {
                        "mapas": [{"pontos_de_interesse": [{"id": "G1"}]}],
                        "setores": [{
                            "conteudo": {
                                "mapas": [{"pontos_de_interesse": [{"id": "S1"}]}],
                                "escaladas": [
                                    {"via_esportiva": {"nome": "Via S", "id_no_mapa": "S1"}},
                                    {"via_esportiva": {"nome": "Via G", "id_no_mapa": "G1"}}
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

def test_validar_referencias_mapa_multiplas_enfiadas():
    croqui = {
        "picos": [{
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "mapas": [{"pontos_de_interesse": [{"id": "BASE"}]}],
                        "escaladas": [{
                            "via_multiplas_enfiadas": {
                                "nome": "Via Longa",
                                "id_no_mapa": "BASE",
                                "enfiadas": [
                                    {"via_esportiva": {"nome": "E1", "id_no_mapa": "ERRO"}}
                                ]
                            }
                        }]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    assert any("E1" in e for e in erros)
    assert any("id_no_mapa 'ERRO'" in e for e in erros)
    assert any("* IDs de mapa disponíveis no contexto: ['BASE']" in e for e in erros)

def test_validar_referencias_mapa_com_grupo_e_ids_disponiveis():
    croqui = {
        "picos": [{
            "nome": "Pico 1",
            "mapas": [{"pontos_de_interesse": [{"id": "MAPA_PICO"}]}],
            "setores_ou_grupos": [{
                "grupo": {
                    "conteudo": {
                        "nome": "Grupo 1",
                        "mapas": [{"pontos_de_interesse": [{"id": "MAPA_GRUPO"}]}],
                        "setores": [{
                            "conteudo": {
                                "nome": "Setor 1",
                                "escaladas": [{"via_esportiva": {"nome": "Via 1", "id_no_mapa": "ERRO"}}]
                            }
                        }]
                    }
                }
            }]
        }]
    }
    erros = validar_referencias_mapa(croqui)
    # Deve mostrar o caminho completo: Pico -> Grupo -> Setor
    # E mostrar os IDs disponíveis: MAPA_PICO e MAPA_GRUPO
    assert any("Grupo 'Grupo 1'" in e for e in erros)
    assert any("IDs de mapa disponíveis no contexto: ['MAPA_GRUPO', 'MAPA_PICO']" in e for e in erros)

from unittest.mock import patch, MagicMock
from scripts.preparar_submissao_lib import compilar_croqui

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
    assert "AVISO: Inconsistência de IDs nos mapas:" in captured.out
    assert "Erro de ID 1" in captured.out
    assert "Erro de ID 2" in captured.out

def test_validar_referencias_mapa_ignora_se_nao_houver_pois_em_lugar_nenhum():
    croqui = {
        "picos": [{
            "nome": "Pico Sem POIs",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor Sem POIs",
                        "mapas": [], # Nenhum mapa ou POI
                        "escaladas": [{"via_esportiva": {"nome": "Via 1", "id_no_mapa": "1"}}]
                    }
                }
            }]
        }]
    }
    # Antes da correção, isso retornaria um aviso sobre a Via 1.
    # Agora deve retornar vazio porque não há nenhum POI no croqui inteiro.
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
