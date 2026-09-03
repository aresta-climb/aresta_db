# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

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
    compilar_croqui,
    precompilar_linhas_mapas_recursivo
)

def test_validar_poi_sem_id_lanca_erro():
    obj = {
        "pontos_de_interesse": [
            {"circulo": {"x": 10, "y": 20, "raio": 5}}
        ]
    }
    with pytest.raises(ValueError, match="campo obrigatório 'id'"):
        validar_pontos_de_interesse_recursivo(obj)


def test_validar_poi_com_id_em_branco_lanca_erro():
    obj = {
        "pontos_de_interesse": [
            {"id": "   ", "circulo": {"x": 10, "y": 20, "raio": 5}}
        ]
    }
    with pytest.raises(ValueError, match="campo obrigatório 'id'"):
        validar_pontos_de_interesse_recursivo(obj)


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

from scripts.preparar_submissao_lib import garantir_comentarios_licenca

def test_yaml_sem_spdx(tmp_path):
    p = tmp_path / "croqui_sem_spdx.yaml"
    p.write_text("id: teste\nnome: Sem SPDX\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[1].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert "id: teste" in "".join(linhas)

def test_yaml_com_spdx(tmp_path):
    p = tmp_path / "croqui_com_spdx.yaml"
    p.write_text("# SPDX-License-Identifier: ODbL-1.0\nid: teste2\nnome: Com SPDX\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_spdx(tmp_path):
    p = tmp_path / "pico_sem_spdx.md"
    p.write_text("---\nnome: Pico\n---\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"

def test_md_com_spdx(tmp_path):
    p = tmp_path / "pico_com_spdx.md"
    p.write_text("---\n# SPDX-License-Identifier: ODbL-1.0\nnome: Pico 2\n---\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_frontmatter(tmp_path):
    p = tmp_path / "pico_sem_frontmatter.md"
    p.write_text("# Titulo\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert "SPDX-License-Identifier" not in texto

def test_yaml_corrige_spdx_errado_ou_incompleto(tmp_path):
    p = tmp_path / "croqui_corrige.yaml"
    # YAML com licença errada e sem copyright, além de um comentário normal
    p.write_text("# Meu comentário\n# SPDX-License-Identifier: CC-BY\nid: corrige\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[1].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert linhas[2].strip() == "# Meu comentário"
    assert "id: corrige" in "".join(linhas)

def test_md_corrige_spdx_errado_ou_incompleto(tmp_path):
    p = tmp_path / "pico_corrige.md"
    # MD com licença errada e copyright errado no frontmatter
    conteudo = "---\n# copyright do ze\n# SPDX-License-Identifier: Outra-Coisa\n# spdx-license-identifier: duplicado\nnome: Pico\n---\nCorpo\n"
    p.write_text(conteudo, encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert linhas[3].strip() == "nome: Pico"
    assert "copyright do ze" not in "".join(linhas).lower()
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

from scripts.preparar_submissao_lib import garantir_comentarios_licenca

def test_yaml_sem_spdx(tmp_path):
    p = tmp_path / "croqui_sem_spdx.yaml"
    p.write_text("id: teste\nnome: Sem SPDX\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[1].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert "id: teste" in "".join(linhas)

def test_yaml_com_spdx(tmp_path):
    p = tmp_path / "croqui_com_spdx.yaml"
    p.write_text("# SPDX-License-Identifier: ODbL-1.0\nid: teste2\nnome: Com SPDX\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_spdx(tmp_path):
    p = tmp_path / "pico_sem_spdx.md"
    p.write_text("---\nnome: Pico\n---\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"

def test_md_com_spdx(tmp_path):
    p = tmp_path / "pico_com_spdx.md"
    p.write_text("---\n# SPDX-License-Identifier: ODbL-1.0\nnome: Pico 2\n---\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert texto.count("SPDX-License-Identifier") == 1

def test_md_sem_frontmatter(tmp_path):
    p = tmp_path / "pico_sem_frontmatter.md"
    p.write_text("# Titulo\n\nTexto\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        texto = f.read()
    assert "SPDX-License-Identifier" not in texto

def test_yaml_corrige_spdx_errado_ou_incompleto(tmp_path):
    p = tmp_path / "croqui_corrige.yaml"
    # YAML com licença errada e sem copyright, além de um comentário normal
    p.write_text("# Meu comentário\n# SPDX-License-Identifier: CC-BY\nid: corrige\n", encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[1].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert linhas[2].strip() == "# Meu comentário"
    assert "id: corrige" in "".join(linhas)

def test_md_corrige_spdx_errado_ou_incompleto(tmp_path):
    p = tmp_path / "pico_corrige.md"
    # MD com licença errada e copyright errado no frontmatter
    conteudo = "---\n# copyright do ze\n# SPDX-License-Identifier: Outra-Coisa\n# spdx-license-identifier: duplicado\nnome: Pico\n---\nCorpo\n"
    p.write_text(conteudo, encoding="utf-8")
    garantir_comentarios_licenca(p)
    with open(p, "r", encoding="utf-8") as f:
        linhas = f.readlines()
    assert linhas[0].strip() == "---"
    assert linhas[1].strip() == "# SPDX-License-Identifier: ODbL-1.0"
    assert linhas[2].strip() == "# Copyright (C) 2026 Aresta Climb Contributors"
    assert linhas[3].strip() == "nome: Pico"
    assert "copyright do ze" not in "".join(linhas).lower()


from scripts.preparar_submissao_lib import (
    computar_precomputados_setor,
    computar_precomputados_grupo,
    computar_precomputados_pico,
    injetar_precomputados
)

def test_computar_precomputados_setor():
    setor = {
        "escaladas": [
            {"via_esportiva": {"nome": "Via 1"}},
            {"via_multiplas_enfiadas": {"nome": "Paredao", "enfiadas": [{}]}},
            {"boulder": {"nome": "B1"}},
            {"tradicional": {"nome": "Movel"}},
            {"highline": {"nome": "Highline 1"}}
        ]
    }
    computar_precomputados_setor(setor)
    assert setor["precomputados"]["total_escaladas"] == 5
    assert setor["precomputados"]["total_esportivas"] == 1
    assert setor["precomputados"]["total_multiplas_enfiadas"] == 1
    assert setor["precomputados"]["total_boulders"] == 1
    assert setor["precomputados"]["total_moveis"] == 1
    assert setor["precomputados"]["total_highlines"] == 1

def test_computar_precomputados_vazio():
    setor = {"escaladas": []}
    computar_precomputados_setor(setor)
    assert len(setor["precomputados"]) == 0

def test_computar_precomputados_grupo():
    grupo = {
        "setores": [
            {"conteudo": {"precomputados": {"total_escaladas": 2, "total_esportivas": 2, "total_moveis": 0, "total_boulders": 0, "total_multiplas_enfiadas": 0, "total_highlines": 0}}},
            {"conteudo": {"precomputados": {"total_escaladas": 3, "total_esportivas": 1, "total_moveis": 1, "total_boulders": 1, "total_multiplas_enfiadas": 0, "total_highlines": 0}}}
        ]
    }
    computar_precomputados_grupo(grupo)
    assert grupo["precomputados"]["total_escaladas"] == 5
    assert grupo["precomputados"]["total_esportivas"] == 3
    assert grupo["precomputados"]["total_moveis"] == 1
    assert grupo["precomputados"]["total_boulders"] == 1
    assert "total_multiplas_enfiadas" not in grupo["precomputados"]
    assert "total_highlines" not in grupo["precomputados"]

def test_computar_precomputados_pico():
    pico = {
        "setores_ou_grupos": [
            {"setor": {"conteudo": {"precomputados": {"total_escaladas": 2, "total_esportivas": 2, "total_moveis": 0, "total_boulders": 0, "total_multiplas_enfiadas": 0, "total_highlines": 0}}}},
            {"grupo": {"conteudo": {"precomputados": {"total_escaladas": 3, "total_esportivas": 1, "total_moveis": 1, "total_boulders": 1, "total_multiplas_enfiadas": 0, "total_highlines": 0}, "setores": [{}, {}]}}},
            {"setor": {"conteudo": {"precomputados": {"total_escaladas": 1, "total_esportivas": 0, "total_moveis": 0, "total_boulders": 0, "total_multiplas_enfiadas": 1, "total_highlines": 0}}}}
        ]
    }
    computar_precomputados_pico(pico)
    assert pico["precomputados"]["total_escaladas"] == 6
    assert pico["precomputados"]["total_setores"] == 4  # 2 standalone + 2 in grupo
    assert pico["precomputados"]["total_grupos"] == 1
    assert pico["precomputados"]["total_esportivas"] == 3
    assert pico["precomputados"]["total_moveis"] == 1
    assert pico["precomputados"]["total_boulders"] == 1
    assert pico["precomputados"]["total_multiplas_enfiadas"] == 1
    assert "total_highlines" not in pico["precomputados"]

def test_injetar_precomputados():
    croqui = {
        "picos": [
            {
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "conteudo": {
                                "escaladas": [{"via_esportiva": {}}, {"via_esportiva": {}}]
                            }
                        }
                    },
                    {
                        "grupo": {
                            "conteudo": {
                                "setores": [
                                    {"conteudo": {"escaladas": [{"boulder": {}}]}}
                                ]
                            }
                        }
                    }
                ]
            }
        ]
    }
    injetar_precomputados(croqui)
    pico = croqui["picos"][0]
    assert pico["setores_ou_grupos"][0]["setor"]["conteudo"]["precomputados"]["total_escaladas"] == 2
    assert pico["setores_ou_grupos"][0]["setor"]["conteudo"]["precomputados"]["total_esportivas"] == 2
    assert pico["setores_ou_grupos"][1]["grupo"]["conteudo"]["setores"][0]["conteudo"]["precomputados"]["total_escaladas"] == 1
    assert pico["setores_ou_grupos"][1]["grupo"]["conteudo"]["setores"][0]["conteudo"]["precomputados"]["total_boulders"] == 1
    assert pico["setores_ou_grupos"][1]["grupo"]["conteudo"]["precomputados"]["total_escaladas"] == 1
    assert pico["precomputados"]["total_escaladas"] == 3
    assert pico["precomputados"]["total_setores"] == 2
    assert pico["precomputados"]["total_grupos"] == 1
    assert pico["precomputados"]["total_esportivas"] == 2
    assert pico["precomputados"]["total_boulders"] == 1


def test_compilar_croqui_com_betas(tmp_path):
    """
    Testa se o compilador de croqui serializa corretamente o bloco betas de uma escalada.
    """
    import yaml
    from aresta_api.proto.generated import croqui_pb2, beta_pb2
    from scripts.preparar_submissao_lib import compilar_croqui

    pico_dir = tmp_path / "pico_teste"
    pico_dir.mkdir()

    # Cria setor com escalada contendo betas
    setor_md = pico_dir / "setor_1.md"
    setor_conteudo = """---
nome: Setor Teste
escaladas:
  - via_esportiva:
      nome: Via dos Betas
    betas:
      - url: https://www.youtube.com/watch?v=xyz123
        titulo: Beta Completo
        fonte: YOUTUBE
        thumbnail_url: https://img.youtube.com/vi/xyz123/hqdefault.jpg
        resultado_llm:
          llm_confidence_score: 95
          llm_reasoning: Nome e grau batem exatamente com a descrição do vídeo.
        match_multiplas_fontes: true
        match_nome_no_snippet: true
        snippets:
          - Descrição completa do beta
---
Descrição do setor de teste.
"""
    setor_md.write_text(setor_conteudo, encoding="utf-8")

    # Cria croqui.yaml
    croqui_yaml = pico_dir / "croqui.yaml"
    croqui_data = {
        "nome": "Croqui Teste Betas",
        "picos": [
            {
                "nome": "Pico Teste",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "caminho": "setor_1.md"
                        }
                    }
                ]
            }
        ]
    }
    with open(croqui_yaml, "w", encoding="utf-8") as f:
        yaml.dump(croqui_data, f)

    destino_yaml = tmp_path / "compilado.yaml"
    destino_binarypb = tmp_path / "compilado.binarypb"

    compilar_croqui(pico_dir, destino_yaml, destino_binarypb)

    # Lê o binarypb gerado e valida o bloco betas
    croqui_msg = croqui_pb2.Croqui()
    with open(destino_binarypb, "rb") as f:
        croqui_msg.ParseFromString(f.read())

    setor = croqui_msg.picos[0].setores_ou_grupos[0].setor.conteudo
    assert len(setor.escaladas) == 1
    escalada = setor.escaladas[0]
    assert escalada.via_esportiva.nome == "Via dos Betas"
    assert len(escalada.betas) == 1

    beta = escalada.betas[0]
    assert beta.url == "https://www.youtube.com/watch?v=xyz123"
    assert beta.titulo == "Beta Completo"
    assert beta.fonte == beta_pb2.FonteMidia.YOUTUBE
    assert beta.thumbnail_url == "https://img.youtube.com/vi/xyz123/hqdefault.jpg"
    assert beta.resultado_llm.llm_confidence_score == 95
    assert beta.resultado_llm.llm_reasoning == "Nome e grau batem exatamente com a descrição do vídeo."
    assert beta.match_multiplas_fontes is True
    assert beta.match_nome_no_snippet is True
    assert len(beta.snippets) == 1
    assert beta.snippets[0] == "Descrição completa do beta"


def test_precompilar_linhas_mapas_recursivo_valida_protobuf():
    """Testa que precompilar_linhas_mapas_recursivo gera campos compatíveis com o schema Protobuf."""
    from scripts.preparar_submissao_lib import precompilar_linhas_mapas_recursivo
    from aresta_api.proto.generated import croqui_pb2
    from google.protobuf import json_format
    
    croqui_data = {
        "id": "teste_croqui",
        "nome": "Croqui Teste",
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{
                            "pontos_de_interesse": [{
                                "id": "linha_1",
                                "linha": {
                                    "conteudo": {
                                        "nos": [
                                            {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},
                                            {"x": 50, "y": 80, "tipo": 3},
                                            {"x": 90, "y": 120, "tipo": 5}
                                        ]
                                    }
                                }
                            }]
                        }]
                    }
                }
            }]
        }]
    }
    
    precompilar_linhas_mapas_recursivo(croqui_data)
    
    pt = croqui_data["picos"][0]["setores_ou_grupos"][0]["setor"]["conteudo"]["mapas"][0]["pontos_de_interesse"][0]
    assert "compilado" in pt["linha"]
    assert "conteudo" not in pt["linha"]
    
    # Verifica marcadores
    marcadores = pt["linha"]["compilado"]["marcadores"]
    assert len(marcadores) == 3
    # O campo no schema é angulo_graus_x100
    assert "angulo_graus_x100" in marcadores[0]
    assert "angulo_tangente_graus_x100" not in marcadores[0]
    
    # Valida no Protobuf
    msg = croqui_pb2.Croqui()
    json_format.ParseDict(croqui_data, msg, ignore_unknown_fields=False)


def test_precompilar_linhas_mapas_ignora_nos_passagem_em_marcadores():
    """Testa que nós de PASSAGEM (tipo 0, 'PASSAGEM' ou omitido) não geram marcadores compilados."""
    from scripts.preparar_submissao_lib import precompilar_linhas_mapas_recursivo
    from aresta_api.proto.generated import croqui_pb2
    from google.protobuf import json_format

    croqui_data = {
        "id": "teste_passagem",
        "nome": "Croqui Teste",
        "picos": [{
            "nome": "Pico 1",
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "nome": "Setor 1",
                        "mapas": [{
                            "pontos_de_interesse": [{
                                "id": "linha_com_passagens",
                                "linha": {
                                    "conteudo": {
                                        "nos": [
                                            {"x": 10, "y": 20, "tipo": 1, "rotulo": "1"},
                                            {"x": 30, "y": 40, "tipo": 0},
                                            {"x": 50, "y": 60, "tipo": "PASSAGEM"},
                                            {"x": 70, "y": 80},
                                            {"x": 90, "y": 100, "tipo": 3},
                                            {"x": 110, "y": 120, "tipo": 5},
                                        ]
                                    }
                                }
                            }]
                        }]
                    }
                }
            }]
        }]
    }

    precompilar_linhas_mapas_recursivo(croqui_data)

    pt = croqui_data["picos"][0]["setores_ou_grupos"][0]["setor"]["conteudo"]["mapas"][0]["pontos_de_interesse"][0]
    compilado = pt["linha"]["compilado"]

    # O caminho SVG ainda contém todos os 6 pontos
    assert "caminho_svg" in compilado
    assert len(compilado["caminho_svg"]) > 0

    # Apenas os 3 nós semânticos (1, 3, 5) geram marcadores
    marcadores = compilado["marcadores"]
    assert len(marcadores) == 3
    tipos = [m["tipo"] for m in marcadores]
    assert tipos == [1, 3, 5]

    # Validação rigorosa no Protobuf
    msg = croqui_pb2.Croqui()
    json_format.ParseDict(croqui_data, msg, ignore_unknown_fields=False)


def test_precompilar_linhas_mapas_propaga_raio_e_tamanho_fonte_nos_marcadores():
    from aresta_api.proto.generated import croqui_pb2
    from google.protobuf import json_format

    croqui_data = {
        "picos": [{
            "setores_ou_grupos": [{
                "setor": {
                    "conteudo": {
                        "mapas": [{
                            "pontos_de_interesse": [{
                                "id": "via_1",
                                "linha": {
                                    "conteudo": {
                                        "nos": [
                                            {"x": 10, "y": 20, "tipo": 1, "rotulo": "1", "raio": 20, "tamanho_fonte": 12},
                                            {"x": 90, "y": 100, "tipo": 5},
                                        ]
                                    }
                                }
                            }]
                        }]
                    }
                }
            }]
        }]
    }

    precompilar_linhas_mapas_recursivo(croqui_data)
    pt = croqui_data["picos"][0]["setores_ou_grupos"][0]["setor"]["conteudo"]["mapas"][0]["pontos_de_interesse"][0]
    marcadores = pt["linha"]["compilado"]["marcadores"]
    assert len(marcadores) == 2
    assert marcadores[0]["raio"] == 20
    assert marcadores[0]["tamanho_fonte"] == 12

    # Validação rigorosa no Protobuf
    msg = croqui_pb2.Croqui()
    json_format.ParseDict(croqui_data, msg, ignore_unknown_fields=False)



