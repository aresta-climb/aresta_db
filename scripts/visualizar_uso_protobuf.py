# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
import graphviz

# Adiciona a raiz ao sys.path para importar módulos do projeto
sys.path.append(str(Path(__file__).resolve().parent.parent))

from aresta_api.proto.generated import croqui_pb2, indice_pb2
from scripts.visualizar_uso_protobuf_lib import DescriptorParser, BinaryPbCounter, GraphvizRenderer
from editor.core.proto_comments import get_proto_comments

def inject_instant_tooltips(svg_path: Path):
    content = svg_path.read_text(encoding='utf-8')
    
    # Remove as tags de tooltip do SO já no arquivo estático para evitar "piscada" do tooltip nativo
    content = content.replace('xlink:title=', 'data-tooltip=')
    
    # Remove todas as tags <title> nativas do Graphviz para eliminar tooltips residuais do SO (como o nome da mensagem)
    import re
    content = re.sub(r'<title>.*?</title>', '', content, flags=re.DOTALL)
    
    script = """
<script type="text/javascript"><![CDATA[
window.addEventListener('load', function() {
    var svg = document.documentElement;
    var fo = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
    fo.setAttribute('width', '400');
    fo.setAttribute('height', '300');
    fo.setAttribute('pointer-events', 'none');
    fo.style.visibility = 'hidden';
    fo.style.overflow = 'visible';

    // Em um documento puramente XML/SVG, precisamos especificar o namespace HTML para elementos do DOM
    var div = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
    div.style.backgroundColor = '#1e1e1e';
    div.style.color = '#ffffff';
    div.style.padding = '10px 14px';
    div.style.borderRadius = '6px';
    div.style.fontFamily = 'Arial, sans-serif';
    div.style.fontSize = '14px';
    div.style.lineHeight = '1.4';
    div.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
    div.style.display = 'inline-block';
    div.style.maxWidth = '350px';
    div.style.wordWrap = 'break-word';
    div.style.border = '1px solid #444';
    
    fo.appendChild(div);
    svg.appendChild(fo);

    var links = document.querySelectorAll('a');
    links.forEach(function(a) {
        var title = a.getAttribute('data-tooltip');
        if (title) {
            a.addEventListener('mouseenter', function(e) {
                div.textContent = title;
                fo.style.visibility = 'visible';
            });
            a.addEventListener('mousemove', function(e) {
                var mouseX = e.clientX;
                var mouseY = e.clientY;
                
                var rect = div.getBoundingClientRect();
                var tw = rect.width || 350;
                var th = rect.height || 100;
                
                var svgRect = svg.getBoundingClientRect();
                
                var xOffset = 15;
                var yOffset = 15;
                
                // Calcula a posição relativa do mouse dentro do SVG
                if (mouseX - svgRect.left + xOffset + tw > svgRect.width) {
                    xOffset = -tw - 15;
                }
                
                if (mouseY - svgRect.top + yOffset + th > svgRect.height) {
                    yOffset = -th - 15;
                }
                
                var pt = svg.createSVGPoint();
                pt.x = mouseX + xOffset;
                pt.y = mouseY + yOffset;
                var svgP = pt.matrixTransform(svg.getScreenCTM().inverse());
                
                fo.setAttribute('x', svgP.x);
                fo.setAttribute('y', svgP.y);
            });
            a.addEventListener('mouseleave', function(e) {
                fo.style.visibility = 'hidden';
            });
        }
    });
});
]]></script>
</svg>
"""
    if '</svg>' in content and 'foreignObject' not in content:
        content = content.replace('</svg>', script)
        svg_path.write_text(content, encoding='utf-8')

def render_graphviz(dot_content: str, name: str, reports_dir: Path):
    dot_path = reports_dir / f"{name}.dot"
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot_content)
        
    try:
        src = graphviz.Source(dot_content)
        # O render salva como {directory}/{filename}.svg e exclui os arquivos temporários criados pela lib (cleanup=True)
        svg_path = src.render(filename=name, directory=str(reports_dir), format="svg", cleanup=True)
        
        # Injeta tooltips interativos instantâneos pós-renderização
        inject_instant_tooltips(Path(svg_path))
        
        print(f"Sucesso: {svg_path} e {dot_path} criados.")
    except graphviz.ExecutableNotFound:
        print(f"[AVISO] O binário 'dot' do Graphviz não foi encontrado no PATH.")
        print(f"O arquivo {dot_path} foi salvo na pasta, mas o SVG não pôde ser gerado.")
        print(f"Instale o Graphviz no seu sistema (ex: https://graphviz.org/download/) para ver as imagens.")

def main():
    parser = argparse.ArgumentParser(description="Gera visualização em grafo do uso dos campos do Protobuf no banco atual.")
    args = parser.parse_args()
    
    root_dir = Path(__file__).resolve().parent.parent
    generated_dir = root_dir / "generated"
    reports_dir = root_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    print("Iniciando varredura das mensagens Protobuf...")
    
    # Instanciando os Parsers
    desc_parser_croqui = DescriptorParser()
    croqui_messages = desc_parser_croqui.parse(croqui_pb2.Croqui.DESCRIPTOR)
    
    desc_parser_indice = DescriptorParser()
    indice_messages = desc_parser_indice.parse(indice_pb2.Indice.DESCRIPTOR)
    
    # Instanciando os Contadores
    croqui_counter = BinaryPbCounter()
    indice_counter = BinaryPbCounter()
    
    # Processa Croquis
    print("Analisando croquis em generated/ ...")
    for croqui_folder in generated_dir.iterdir():
        if not croqui_folder.is_dir():
            continue
        compilado_path = croqui_folder / "compilado.binarypb"
        if compilado_path.exists():
            with open(compilado_path, "rb") as f:
                croqui = croqui_pb2.Croqui()
                croqui.ParseFromString(f.read())
                
                is_pub = croqui.publicar_croqui
                croqui_counter.process_file_message(croqui, is_pub)
                
    # Processa Índice
    print("Analisando o índice global...")
    indice_path = generated_dir / "indice.binarypb"
    custom_totals_indice = {}
    if indice_path.exists():
        with open(indice_path, "rb") as f:
            indice = indice_pb2.Indice()
            indice.ParseFromString(f.read())
            
            # Conta a raiz (vai descer nas filhas, mas sobrescreveremos)
            indice_counter.process_file_message(indice, is_published=True)
            
            resumo_counter = BinaryPbCounter()
            for resumo in indice.croquis:
                resumo_counter.process_file_message(resumo, is_published=True)
                
            # Mescla as contagens na raiz
            for full_name, fields in resumo_counter.counts.items():
                indice_counter.counts[full_name] = fields
            for full_name, msg_tots in resumo_counter.message_totals.items():
                indice_counter.message_totals[full_name] = msg_tots
                
            # Garante que todas as mensagens aninhadas usem o total de croquis (mesmo se contagem for 0)
            for full_name in indice_messages.keys():
                if full_name != "aresta.Indice":
                    custom_totals_indice[full_name] = resumo_counter.total_all
            
    # Geração dos Graphviz DOTs
    print("Gerando arquivos do Graphviz...")
    
    # Extract comments for tooltips
    comments = get_proto_comments()

    # Render Croqui Completo
    croqui_renderer = GraphvizRenderer(croqui_messages, croqui_counter, comments=comments)
    croqui_dot = croqui_renderer.render()
    render_graphviz(croqui_dot, "croqui_completo", reports_dir)
    
    # Render Croqui Usado
    croqui_renderer_usado = GraphvizRenderer(croqui_messages, croqui_counter, filter_unused=True, comments=comments)
    croqui_dot_usado = croqui_renderer_usado.render()
    render_graphviz(croqui_dot_usado, "croqui_usado", reports_dir)
    
    # Render Índice Completo
    indice_renderer = GraphvizRenderer(indice_messages, indice_counter, single_column=True, custom_totals=custom_totals_indice, comments=comments)
    indice_dot = indice_renderer.render()
    render_graphviz(indice_dot, "indice_completo", reports_dir)
    
    # Render Índice Usado
    indice_renderer_usado = GraphvizRenderer(indice_messages, indice_counter, single_column=True, custom_totals=custom_totals_indice, filter_unused=True, comments=comments)
    indice_dot_usado = indice_renderer_usado.render()
    render_graphviz(indice_dot_usado, "indice_usado", reports_dir)
    
    print("Concluído!")

if __name__ == "__main__":
    main()
