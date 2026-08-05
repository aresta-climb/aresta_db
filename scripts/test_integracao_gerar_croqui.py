# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
from pathlib import Path
import tempfile
import zipfile
import shutil
import sys

# Garante que scripts está no path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gerar_croqui_experimental import empacotar_databases_para_croqui

def test_empacotar_database_para_croqui_integracao(tmp_path: Path):
    """
    Testa de ponta a ponta a geração de um croqui experimental ofuscado
    a partir de uma pasta válida de database/.
    """
    # 1. Cria uma estrutura mínima e válida de database/
    db_fake = tmp_path / "database" / "pico_teste_integracao"
    db_fake.mkdir(parents=True)
    
    # croqui.yaml mínimo válido para não quebrar o deploy_generated
    croqui_yaml_conteudo = """
id: pico_teste_integracao
nome: Pico Teste Integração
descricao: Croqui para teste
caminho_thumbnail: imagens/fake.jpg
picos:
  - nome: Pico Teste Integração
    estado: SP
"""
    (db_fake / "croqui.yaml").write_text(croqui_yaml_conteudo, encoding="utf-8")
    
    # Pasta de imagens mínima com JPEG válido
    (db_fake / "imagens").mkdir()
    from PIL import Image
    img = Image.new('RGB', (1, 1), color='red')
    img.save(db_fake / "imagens" / "fake.jpg")
    
    output_dir = tmp_path / "saida_croqui"
    output_dir.mkdir()
    
    # 2. Invoca o empacotador (que deve rodar o deploy local e criar o zip ofuscado)
    arquivo_gerado = empacotar_databases_para_croqui([db_fake], output_dir)
    
    # 3. Asserções
    assert arquivo_gerado.exists(), "O arquivo .croqui não foi gerado."
    assert arquivo_gerado.suffix == ".croqui", "A extensão do arquivo deve ser .croqui."
    
    # 4. Desfaz a ofuscação (XOR 0xFF no primeiro byte) para validar o ZIP
    with open(arquivo_gerado, "r+b") as f:
        primeiro_byte = f.read(1)
        f.seek(0)
        byte_desofuscado = bytes([primeiro_byte[0] ^ 0xFF])
        f.write(byte_desofuscado)
        f.flush()
        
    with zipfile.ZipFile(arquivo_gerado, "r") as zf:
        arquivos = zf.namelist()
        
        # No novo comportamento do empacotar_croqui, os arquivos são zipados a partir da raiz da pasta
        assert "croqui_experimental.yaml" in arquivos, "Falta o croqui_experimental.yaml"
        assert any(f.startswith(f"database/pico_teste_integracao/croqui.yaml") for f in arquivos), "Falta o database"
        assert any(f.startswith(f"compilado/") for f in arquivos), "Falta o compilado gerado pelo deploy"
        
        # Garante que os arquivos globais do deploy foram gerados e empacotados
        assert "compilado/indice.binarypb" in arquivos, "Falta o indice.binarypb no compilado"
        assert "compilado/arquivos_serving.yaml" in arquivos, "Falta o arquivos_serving.yaml no compilado"
        assert "compilado/thumbnails/pico_teste_integracao.webp" in arquivos, "Falta a thumbnail compilada"

def test_empacotar_multiplos_databases_para_croqui_integracao(tmp_path: Path):
    """
    Testa de ponta a ponta a geração de um único croqui experimental ofuscado
    a partir de múltiplas pastas do database/.
    """
    db_fake1 = tmp_path / "database" / "pico_1"
    db_fake1.mkdir(parents=True)
    croqui_yaml_1 = "id: pico_1\nnome: Pico 1\ncaminho_thumbnail: imagens/fake.jpg\npicos:\n  - nome: Pico 1\n    estado: SP\n"
    (db_fake1 / "croqui.yaml").write_text(croqui_yaml_1, encoding="utf-8")
    (db_fake1 / "imagens").mkdir()
    from PIL import Image
    img = Image.new('RGB', (1, 1), color='red')
    img.save(db_fake1 / "imagens" / "fake.jpg")
    
    db_fake2 = tmp_path / "database" / "pico_2"
    db_fake2.mkdir(parents=True)
    croqui_yaml_2 = "id: pico_2\nnome: Pico 2\ncaminho_thumbnail: imagens/fake.jpg\npicos:\n  - nome: Pico 2\n    estado: RJ\n"
    (db_fake2 / "croqui.yaml").write_text(croqui_yaml_2, encoding="utf-8")
    (db_fake2 / "imagens").mkdir()
    img.save(db_fake2 / "imagens" / "fake.jpg")
    
    output_dir = tmp_path / "saida_croqui"
    output_dir.mkdir()
    
    arquivo_gerado = empacotar_databases_para_croqui([db_fake1, db_fake2], output_dir)
    
    assert arquivo_gerado.exists()
    assert arquivo_gerado.name.endswith("_modificados.croqui")
    
    # Desfaz a ofuscação
    with open(arquivo_gerado, "r+b") as f:
        primeiro_byte = f.read(1)
        f.seek(0)
        byte_desofuscado = bytes([primeiro_byte[0] ^ 0xFF])
        f.write(byte_desofuscado)
        f.flush()
        
    with zipfile.ZipFile(arquivo_gerado, "r") as zf:
        arquivos = zf.namelist()
        
        # O metadado base
        assert "croqui_experimental.yaml" in arquivos
        
        # Assegura que ambos os bancos de dados foram embutidos
        assert any(f.startswith("database/pico_1/croqui.yaml") for f in arquivos), "Pico 1 não embutido"
        assert any(f.startswith("database/pico_2/croqui.yaml") for f in arquivos), "Pico 2 não embutido"
        
        # Assegura que ambos os compilados foram embutidos pelo deploy_generated
        # A pasta compilado terá compilado/pico_1 e compilado/pico_2
        assert any("compilado/pico_1" in f for f in arquivos), "Pico 1 não compilado"
        assert any("compilado/pico_2" in f for f in arquivos), "Pico 2 não compilado"
        
        # Garante que os arquivos globais do deploy foram gerados e empacotados
        assert "compilado/indice.binarypb" in arquivos, "Falta o indice.binarypb no compilado"
        assert "compilado/arquivos_serving.yaml" in arquivos, "Falta o arquivos_serving.yaml no compilado"
        assert "compilado/thumbnails/pico_1.webp" in arquivos, "Falta a thumbnail compilada do pico 1"
        assert "compilado/thumbnails/pico_2.webp" in arquivos, "Falta a thumbnail compilada do pico 2"
