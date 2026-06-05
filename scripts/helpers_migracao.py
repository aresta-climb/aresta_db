# Copyright (C) 2026 ARESTA
#
# Este arquivo é livre; você pode redistribuí-lo e/ou modificá-lo
# sob os termos da Licença Pública Geral GNU.

import yaml
import textwrap
from pathlib import Path
from scripts.preparar_submissao_lib import parse_md_com_frontmatter

def configurar_croqui_teste(caminho_temp: Path, yaml_content: str, arquivos: dict[str, str] = None) -> Path:
    """
    Configura uma estrutura fictícia de croqui em um diretório temporário para testes.
    """
    croqui_dir = caminho_temp / "croqui_teste"
    croqui_dir.mkdir(parents=True, exist_ok=True)
    
    # Cria o croqui.yaml
    croqui_yaml_path = croqui_dir / "croqui.yaml"
    with open(croqui_yaml_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(yaml_content).strip())
        
    # Cria arquivos de conteúdo adicionais (.md)
    if arquivos:
        for nome_arquivo, conteudo in arquivos.items():
            caminho_arquivo = croqui_dir / nome_arquivo
            caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(textwrap.dedent(conteudo).strip())
                
    return croqui_dir

def carregar_yaml_migrado(croqui_dir: Path) -> dict:
    """
    Retorna o croqui.yaml migrado em formato de dicionário.
    """
    caminho_yaml = croqui_dir / "croqui.yaml"
    with open(caminho_yaml, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def carregar_markdown_migrado(croqui_dir: Path, caminho_relativo: str) -> tuple[dict, str]:
    """
    Lê e retorna o frontmatter e o corpo de um arquivo markdown migrado.
    """
    caminho_md = croqui_dir / caminho_relativo
    return parse_md_com_frontmatter(caminho_md)
