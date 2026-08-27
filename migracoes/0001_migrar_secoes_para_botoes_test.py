# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import importlib.util
from pathlib import Path
from scripts.helpers_migracao import configurar_croqui_teste, carregar_yaml_migrado

# Carrega a migração dinamicamente devido à restrição de nomes começando com números em imports Python
caminho_migracao = Path(__file__).resolve().parent / "0001_migrar_secoes_para_botoes.py"
spec = importlib.util.spec_from_file_location("migracao_0001", str(caminho_migracao))
migracao_modulo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migracao_modulo)
migrar = migracao_modulo.migrar


def test_migracao_secoes_textuais_para_botoes(tmp_path):
    # DADO um croqui antigo no formato "secoes_textuais"
    yaml_antigo = """
    id: br_mg_teste
    nome: Pico Teste
    secoes_textuais:
      - titulo: Capa Principal
        caminho: capa.md
      - titulo: Acesso
        caminho: acesso.md
    """
    
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_antigo)
    
    # QUANDO executamos a migração
    migrar(croqui_dir)
    
    # ENTÃO as chaves antigas devem ter sido removidas e a chave "botoes" estruturada corretamente
    yaml_novo = carregar_yaml_migrado(croqui_dir)
    assert "secoes_textuais" not in yaml_novo
    assert "arquivos_markdown" not in yaml_novo
    assert "botoes" in yaml_novo
    
    botoes = yaml_novo["botoes"]
    assert len(botoes) == 2
    assert botoes[0]["texto"] == "Capa Principal"
    assert botoes[0]["destino"]["secao_textual"]["caminho"] == "capa.md"
    assert botoes[1]["texto"] == "Acesso"
    assert botoes[1]["destino"]["secao_textual"]["caminho"] == "acesso.md"


def test_migracao_arquivos_markdown_antiquados_para_botoes(tmp_path):
    # DADO um croqui antigo no formato "arquivos_markdown"
    yaml_antiquado = """
    id: br_mg_teste_antigo
    nome: Pico Antigo
    arquivos_markdown:
      - titulo: Sobre
        caminho: sobre.md
    """
    
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_antiquado)
    
    # QUANDO executamos a migração
    migrar(croqui_dir)
    
    # ENTÃO as chaves antigas devem ter sido removidas e a chave "botoes" estruturada corretamente
    yaml_novo = carregar_yaml_migrado(croqui_dir)
    assert "arquivos_markdown" not in yaml_novo
    assert "botoes" in yaml_novo
    
    botoes = yaml_novo["botoes"]
    assert len(botoes) == 1
    assert botoes[0]["texto"] == "Sobre"
    assert botoes[0]["destino"]["secao_textual"]["caminho"] == "sobre.md"


def test_migracao_no_op_se_ja_migrado(tmp_path):
    # DADO um croqui que já foi migrado
    yaml_migrado = """
    id: br_mg_teste_migrado
    nome: Pico Migrado
    ultima_migracao: 1
    botoes:
      - texto: Sobre
        destino:
          secao_textual:
            caminho: sobre.md
    """
    
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_migrado)
    
    # QUANDO executamos a migração
    migrar(croqui_dir)
    
    # ENTÃO nada deve mudar no yaml do croqui
    yaml_novo = carregar_yaml_migrado(croqui_dir)
    assert yaml_novo["ultima_migracao"] == 1
    assert len(yaml_novo["botoes"]) == 1
    assert yaml_novo["botoes"][0]["texto"] == "Sobre"


def test_migracao_no_op_se_campos_antigos_nao_existem_sem_ultima_migracao(tmp_path):
    # DADO um croqui sem os campos antigos e sem ultima_migracao setado
    yaml_sem_campos = """
    id: br_mg_teste_sem_campos
    nome: Pico Sem Campos
    botoes:
      - texto: Ajuda
        destino:
          secao_textual:
            caminho: ajuda.md
    """
    
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_sem_campos)
    
    # Capturamos o conteúdo bruto do arquivo
    yaml_path = croqui_dir / "croqui.yaml"
    conteudo_antes = yaml_path.read_text(encoding="utf-8")
    
    # QUANDO executamos a migração
    migrar(croqui_dir)
    
    # ENTÃO o arquivo não deve ser modificado (o conteúdo bruto deve ser idêntico)
    conteudo_depois = yaml_path.read_text(encoding="utf-8")
    assert conteudo_antes == conteudo_depois


