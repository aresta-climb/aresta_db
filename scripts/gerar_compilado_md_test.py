# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import pytest
import yaml
import json
import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gerar_compilado_md import gerar_compilado_md
from scripts.gerar_compilado_md import gerar_compilado_md

def test_gerar_compilado_md(tmp_path, capsys):
    croqui_dir = tmp_path / "pico_test"
    croqui_dir.mkdir()
    
    # Setup partes.json
    partes_data = {
        "capa": [0],
        "setor_01": [1]
    }
    partes_file = croqui_dir / "partes.json"
    partes_file.write_text(json.dumps(partes_data), encoding="utf-8")

    # Setup croqui.yaml
    croqui_data = {
        "id": "pico_test",
        "nome": "Pico de Teste",
        "secoes_textuais": [
            {"titulo": "Capa", "caminho": "capa.md"}
        ],
        "picos": [
            {
                "nome": "Pico de Teste",
                "setores_ou_grupos": [
                    {"setor": {"caminho": "setor_01.md"}}
                ]
            }
        ]
    }
    croqui_file = croqui_dir / "croqui.yaml"
    croqui_file.write_text(yaml.dump(croqui_data), encoding="utf-8")

    # Setup compilado.yaml
    compilado_data = {
        "id": "pico_test",
        "nome": "Pico de Teste",
        "descricao": "Descricao top level.",
        "arquivos_externos": [{"caminho": "imagens/foo.webp"}],
        "secoes_textuais": [
            {
                "titulo": "Capa",
                "conteudo": "Welcome to the cover.",
                "campo_dinamico": "Valor especial que deve aparecer no fim"
            }
        ],
        "picos": [
            {
                "nome": "Pico de Teste",
                "setores_ou_grupos": [
                    {
                        "setor": {
                            "nome": "Setor Princial",
                            "conteudo": {
                                "descricao": "Uma descricao do setor",
                                "mapas": [
                                    {
                                        "caminho_imagem_mapa": "imagens/mapa1.webp",
                                        "pontos_de_interesse": [{"id": "p1", "label": "Via Teste"}]
                                    }
                                ],
                                "escaladas": [
                                    {
                                        "via_esportiva": {
                                            "nome": "Via Teste",
                                            "dificuldade": "BR_6"
                                        }
                                    }
                                ],
                                "campo_dinamico_do_setor": "Outro valor obscuro"
                            }
                        }
                    }
                ]
            }
        ]
    }
    compilado_file = tmp_path / "compilado.yaml"
    compilado_file.write_text(yaml.dump(compilado_data), encoding="utf-8")

    output_md = tmp_path / "compilado.md"
    
    # Run function
    gerar_compilado_md(croqui_dir, compilado_file, output_md)

    # Validate output
    assert output_md.exists()
    content = output_md.read_text(encoding="utf-8")

    # Check top level
    assert "# Croqui: Pico de Teste" in content
    assert "Descricao top level." in content
    
    # Check partes order correctly populated
    assert "## Parte: capa" in content
    assert "Welcome to the cover." in content
    assert "campo_dinamico" in content
    assert "Valor especial que deve aparecer no fim" in content
    
    # Check setor
    assert "## Parte: setor_01" in content
    assert "Setor (Pico: Pico de Teste)" in content
    assert "Uma descricao do setor" in content
    assert "![caminho_imagem_mapa](imagens/mapa1.webp)" in content  # Image renderized OK
    
    # Check escalada nested fields
    assert "**via_esportiva**:" in content
    assert "**dificuldade**: BR_6" in content
    
    # Check missing fallback external files
    assert "## Arquivos Externos" in content
    assert "![caminho](imagens/foo.webp)" in content

    # Assegura que nao imprime log verboso
    captured = capsys.readouterr()
    assert 'gerado com sucesso!' not in captured.out


def test_gerar_compilado_md_com_picos_vazios_e_grupos_sem_setores(tmp_path):
    croqui_dir = tmp_path / "pico_vazio_dir"
    croqui_dir.mkdir()
    
    # croqui.yaml com pico vazio e grupo sem setores
    croqui_data = {
        "id": "pico_vazio",
        "nome": "Pico Vazio",
        "picos": [
            {
                "nome": "Pico Principal",
                "setores_ou_grupos": [
                    {"grupo": {"caminho": "grupo_vazio.md"}}
                ]
            },
            {
                "nome": "Pico Totalmente Vazio",
                "setores_ou_grupos": []
            }
        ]
    }
    (croqui_dir / "croqui.yaml").write_text(yaml.dump(croqui_data), encoding="utf-8")
    
    # compilado.yaml onde grupo tem conteudo vazio ou sem setores filhos
    compilado_data = {
        "id": "pico_vazio",
        "nome": "Pico Vazio",
        "picos": [
            {
                "nome": "Pico Principal",
                "setores_ou_grupos": [
                    {
                        "grupo": {
                            "nome": "Grupo Vazio",
                            "conteudo": {
                                "descricao": "Sem setores filhos",
                                "setores": []
                            }
                        }
                    }
                ]
            },
            {
                "nome": "Pico Totalmente Vazio",
                "setores_ou_grupos": []
            }
        ]
    }
    compilado_file = tmp_path / "compilado_vazio.yaml"
    compilado_file.write_text(yaml.dump(compilado_data), encoding="utf-8")
    
    output_md = tmp_path / "compilado_vazio.md"
    
    # Não deve estourar exceção
    gerar_compilado_md(croqui_dir, compilado_file, output_md)
    assert output_md.exists()
    conteudo = output_md.read_text(encoding="utf-8")
    assert "Pico Totalmente Vazio" in conteudo or "Pico Principal" in conteudo


def test_gerar_compilado_md_com_dados_compilados_nulos(tmp_path):
    croqui_dir = tmp_path / "pico_nulo_dir"
    croqui_dir.mkdir()
    
    # croqui.yaml declarando grupo
    croqui_data = {
        "id": "pico_nulo",
        "nome": "Pico Nulo",
        "picos": [
            {
                "nome": "Pico Teste",
                "setores_ou_grupos": [
                    {"grupo": {"caminho": "grupo_teste.md"}}
                ]
            }
        ]
    }
    (croqui_dir / "croqui.yaml").write_text(yaml.dump(croqui_data), encoding="utf-8")
    
    # compilado.yaml onde o item é None ou não possui a chave 'grupo' (ex: chave 'setor')
    compilado_data = {
        "id": "pico_nulo",
        "nome": "Pico Nulo",
        "picos": [
            {
                "nome": "Pico Teste",
                "setores_ou_grupos": [
                    {
                        "setor": None  # chave divergente ou nula
                    }
                ]
            }
        ]
    }
    compilado_file = tmp_path / "compilado_nulo.yaml"
    compilado_file.write_text(yaml.dump(compilado_data), encoding="utf-8")
    
    output_md = tmp_path / "compilado_nulo.md"
    
    # Deve ser resiliente a NoneType e não estourar AttributeError: 'NoneType' object has no attribute 'get'
    gerar_compilado_md(croqui_dir, compilado_file, output_md)
    assert output_md.exists()


def test_gerar_compilado_md_resiliencia_tipos_invalidos_e_picos_extras(tmp_path):
    croqui_dir = tmp_path / "croqui_extra_dir"
    croqui_dir.mkdir()

    # partes.json com uma parte em ordem e uma fora
    partes = {
        "intro": {"tipo": "arquivo_markdown"},
        "setor_ordem": {"tipo": "setor"}
    }
    (croqui_dir / "partes.json").write_text(json.dumps(partes), encoding="utf-8")

    croqui_data = {
        "id": "croqui_extra",
        "nome": "Croqui Extra",
        "secoes_textuais": [
            {"caminho": "intro.md"},
            {"caminho": "sobre.md"}
        ],
        "picos": [
            "invalido_nao_dict",
            {
                "nome": "Pico 1",
                "setores_ou_grupos": [
                    "nao_dict",
                    {"setor": {"caminho": "setor_ordem.md"}},
                    {"setor": {"caminho": "setor_fora.md"}},
                    {"grupo": {"caminho": "grupo_com_string.md"}}
                ]
            },
            {
                "nome": "Pico 2 Extra", # Pico presente no croqui mas ausente no compilado
                "setores_ou_grupos": [
                    {"setor": {"caminho": "setor_pico2.md"}}
                ]
            }
        ]
    }
    (croqui_dir / "croqui.yaml").write_text(yaml.dump(croqui_data), encoding="utf-8")

    compilado_data = {
        "id": "croqui_extra",
        "nome": "Croqui Extra",
        "secoes_textuais": [
            "Texto direto sem ser dict",  # testa dados como string em arquivo_markdown
            {"titulo": "Sobre", "conteudo": "Detalhes", "autor": "Equipe"}
        ],
        "picos": [
            {
                "nome": "Pico 1",
                "setores_ou_grupos": [
                    {"setor": "Texto simples do setor"}, # testa dados como string
                    {"setor": {"conteudo": "Conteudo string do setor"}},
                    {"setor": {"conteudo": {"grau": "V5"}}},
                    {"grupo": {"conteudo": "Grupo string"}}
                ]
            }
            # Sem o Pico 2 no compilado
        ]
    }
    compilado_file = tmp_path / "compilado_extra.yaml"
    compilado_file.write_text(yaml.dump(compilado_data), encoding="utf-8")

    output_md = tmp_path / "compilado_extra.md"
    gerar_compilado_md(croqui_dir, compilado_file, output_md)

    assert output_md.exists()
    conteudo_md = output_md.read_text(encoding="utf-8")
    assert "Pico 1" in conteudo_md
    assert "Pico 2 Extra" in conteudo_md
    assert "Texto direto sem ser dict" in conteudo_md

