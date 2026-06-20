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
