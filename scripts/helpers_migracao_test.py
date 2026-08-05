# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) Aresta Contributors

# Copyright (C) 2026 ARESTA
#
# Este arquivo é livre; você pode redistribuí-lo e/ou modificá-lo
# sob os termos da Licença Pública Geral GNU.

from pathlib import Path
from scripts.helpers_migracao import configurar_croqui_teste, carregar_yaml_migrado, carregar_markdown_migrado

def test_configurar_e_carregar_croqui_teste(tmp_path):
    """
    Testa a criação de croqui temporário e leitura de arquivos migrados.
    """
    yaml_antigo = """
    id: teste_helper
    nome: Pico Helper
    """
    arquivos = {
        "conteudo/info.md": """
        ---
        secao: Introdução
        ---
        Corpo do markdown aqui.
        """
    }
    
    croqui_dir = configurar_croqui_teste(tmp_path, yaml_content=yaml_antigo, arquivos=arquivos)
    
    # Valida se os arquivos foram criados
    assert (croqui_dir / "croqui.yaml").exists()
    assert (croqui_dir / "conteudo/info.md").exists()
    
    # Testa carregar_yaml_migrado
    dados_yaml = carregar_yaml_migrado(croqui_dir)
    assert dados_yaml["id"] == "teste_helper"
    assert dados_yaml["nome"] == "Pico Helper"
    
    # Testa carregar_markdown_migrado
    frontmatter, corpo = carregar_markdown_migrado(croqui_dir, "conteudo/info.md")
    assert frontmatter["secao"] == "Introdução"
    assert "Corpo do markdown aqui." in corpo
