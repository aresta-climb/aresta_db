# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import pytest
import sys
from pathlib import Path

# Garante que a raiz do projeto (onde a pasta scripts reside) está no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.visualizar_uso_protobuf import inject_instant_tooltips, render_graphviz

def test_inject_instant_tooltips(tmp_path):
    svg_file = tmp_path / "teste.svg"
    svg_content = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
    <a xlink:title="Test Tooltip">
        <title>Test Tooltip</title>
        <rect width="10" height="10"/>
    </a>
</svg>
'''
    svg_file.write_text(svg_content, encoding='utf-8')
    
    inject_instant_tooltips(svg_file)
    
    content = svg_file.read_text(encoding='utf-8')
    assert '<script type="text/javascript">' in content
    assert 'foreignObject' in content
    # O xlink:title foi estaticamente substituído
    assert 'data-tooltip="Test Tooltip"' in content
    assert 'xlink:title' not in content
    
    # Valida a remoção total da tag <title> residual do SO
    assert '<title>' not in content
    
    # Valida a presença da lógica responsiva anti-clipping orientada ao SVG
    assert 'getBoundingClientRect' in content
    assert 'svgRect.width' in content
    assert 'svgRect.height' in content

def test_render_graphviz(tmp_path):
    dot_content = "digraph G { A -> B; }"
    # mockando a execução para checar a saída
    render_graphviz(dot_content, "teste_render", tmp_path)
    
    svg_file = tmp_path / "teste_render.svg"
    dot_file = tmp_path / "teste_render.dot"
    
    assert svg_file.exists()
    assert dot_file.exists()
    
    # O arquivo dot deve ter o conteúdo original
    assert dot_file.read_text(encoding='utf-8') == dot_content
    
    # O arquivo svg gerado pelo graphviz deve conter a injeção do script ao final
    svg_content = svg_file.read_text(encoding='utf-8')
    assert '<script type="text/javascript">' in svg_content
