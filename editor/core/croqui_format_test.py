# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

import pytest
import os
import zipfile
import shutil
from pathlib import Path
from editor.core.croqui_format import empacotar_croqui, ler_croqui, ofuscar_primeiro_byte

def test_ofuscar_primeiro_byte(tmp_path):
    # DADO um arquivo com conteúdo conhecido
    arquivo = tmp_path / "teste.bin"
    conteúdo_original = b"PK\x03\x04" # Início padrão de um ZIP
    arquivo.write_bytes(conteúdo_original)
    
    # QUANDO ofuscar o primeiro byte
    ofuscar_primeiro_byte(arquivo)
    
    # ENTÃO o primeiro byte deve ser diferente (XOR 0xFF)
    conteúdo_ofuscado = arquivo.read_bytes()
    assert conteúdo_ofuscado[0] == conteúdo_original[0] ^ 0xFF
    assert conteúdo_ofuscado[1:] == conteúdo_original[1:]
    
    # E QUANDO ofuscar novamente (desofuscar)
    ofuscar_primeiro_byte(arquivo)
    
    # ENTÃO deve voltar ao original
    assert arquivo.read_bytes() == conteúdo_original

def test_empacotar_croqui_gera_arquivo_ofuscado(tmp_path):
    # DADO uma pasta com arquivos
    pasta_origem = tmp_path / "croqui_origem"
    pasta_origem.mkdir()
    (pasta_origem / "arquivo1.txt").write_text("conteudo 1")
    (pasta_origem / "subpasta").mkdir()
    (pasta_origem / "subpasta" / "arquivo2.txt").write_text("conteudo 2")
    
    caminho_croqui = tmp_path / "teste.croqui"
    
    # QUANDO empacotar
    empacotar_croqui(pasta_origem, caminho_croqui)
    
    # ENTÃO o arquivo deve existir
    assert caminho_croqui.is_file()
    
    # E o primeiro byte NÃO deve ser 'P' (0x50)
    primeiro_byte = caminho_croqui.read_bytes()[:1]
    assert primeiro_byte != b"P"
    assert primeiro_byte == bytes([0x50 ^ 0xFF])

def test_ler_croqui_extrai_corretamente(tmp_path):
    # DADO um arquivo .croqui ofuscado
    pasta_origem = tmp_path / "origem"
    pasta_origem.mkdir()
    (pasta_origem / "info.txt").write_text("dados importantes")
    
    caminho_croqui = tmp_path / "meu.croqui"
    empacotar_croqui(pasta_origem, caminho_croqui)
    
    pasta_destino = tmp_path / "destino"
    
    # QUANDO ler o croqui
    ler_croqui(caminho_croqui, pasta_destino)
    
    # ENTÃO os arquivos devem ser extraídos corretamente
    assert (pasta_destino / "info.txt").is_file()
    assert (pasta_destino / "info.txt").read_text() == "dados importantes"
    
    # E o arquivo original .croqui deve permanecer ofuscado (segurança/consistência)
    assert caminho_croqui.read_bytes()[:1] != b"P"

def test_ler_croqui_com_zip_normal(tmp_path):
    """
    O sistema deve ser robusto o suficiente para tentar ler um ZIP normal 
    se a desofuscação falhar ou se o arquivo já for um ZIP válido.
    """
    # DADO um ZIP normal (sem ofuscação) renomeado para .croqui
    pasta_origem = tmp_path / "origem_zip"
    pasta_origem.mkdir()
    (pasta_origem / "readme.md").write_text("ola")
    
    caminho_zip = tmp_path / "normal.croqui"
    with zipfile.ZipFile(caminho_zip, 'w') as zf:
        zf.write(pasta_origem / "readme.md", arcname="readme.md")
        
    pasta_destino = tmp_path / "destino_zip"
    
    # QUANDO ler o croqui
    # Se ele for um ZIP válido, ele deve extrair mesmo assim (fallback)
    ler_croqui(caminho_zip, pasta_destino)
    
    # ENTÃO deve funcionar
    assert (pasta_destino / "readme.md").read_text() == "ola"
