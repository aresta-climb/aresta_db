# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import io
import argparse
import pymupdf
import shutil
from PIL import Image
from pathlib import Path
import json

def converter_para_webp(pasta_destino_path, imagem_origem_path):
    """Converte uma imagem para WebP com redimensionamento inteligente."""
    imagem_destino_path = pasta_destino_path / f"{imagem_origem_path.stem}.webp"
    with Image.open(imagem_origem_path) as pil_img:
        # Redimensionar se exceder max_area
        max_area = 2048 * 2048
        area = pil_img.width * pil_img.height
        if area > max_area:
            scale = (max_area / area) ** 0.5
            new_width = int(pil_img.width * scale)
            new_height = int(pil_img.height * scale)
            pil_img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
        
        pil_img.save(imagem_destino_path, "WEBP", quality=85)

def _corrigir_pdf_malformado(doc):
    """
    Remove a árvore de estrutura corrompida do PDF para evitar erros de 
    'No common ancestor in structure tree'. Este erro ocorre em PDFs etiquetados
    com estrutura lógica malformada ao tentar manipular páginas.
    """
    try:
        catalog_xref = doc.pdf_catalog()
        doc.xref_set_key(catalog_xref, "StructTreeRoot", "null")
    except Exception:
        # Silenciosamente ignoramos falhas na tentativa de correção
        pass

def _serializar_objeto_pymupdf(obj):
    """Converte objetos do PyMuPDF (Rect, Point, Matrix) em tipos básicos do Python."""
    if isinstance(obj, pymupdf.Rect):
        return [obj.x0, obj.y0, obj.x1, obj.y1]
    if isinstance(obj, pymupdf.Point):
        return [obj.x, obj.y]
    if isinstance(obj, pymupdf.Matrix):
        return [obj.a, obj.b, obj.c, obj.d, obj.e, obj.f]
    if isinstance(obj, pymupdf.Quad):
        return [
            [obj.ul.x, obj.ul.y],
            [obj.ur.x, obj.ur.y],
            [obj.ll.x, obj.ll.y],
            [obj.lr.x, obj.lr.y]
        ]
    if isinstance(obj, dict):
        return {k: _serializar_objeto_pymupdf(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serializar_objeto_pymupdf(i) for i in obj]
    return obj

def translate_coordinates(drawings, text_dict, img_bbox, zoom, img_size_px):
    """Traduz coordenadas globais do PDF para coordenadas locais da imagem extraída."""
    scale_x = img_size_px[0] / img_bbox.width if img_bbox.width else 1.0
    scale_y = img_size_px[1] / img_bbox.height if img_bbox.height else 1.0

    def tx(x): return (x - img_bbox.x0) * scale_x
    def ty(y): return (y - img_bbox.y0) * scale_y
    
    def transform_obj(obj):
        if isinstance(obj, pymupdf.Rect):
            return pymupdf.Rect(tx(obj.x0), ty(obj.y0), tx(obj.x1), ty(obj.y1))
        if isinstance(obj, pymupdf.Point):
            return pymupdf.Point(tx(obj.x), ty(obj.y))
        if isinstance(obj, pymupdf.Quad):
            return pymupdf.Quad(
                pymupdf.Point(tx(obj.ul.x), ty(obj.ul.y)),
                pymupdf.Point(tx(obj.ur.x), ty(obj.ur.y)),
                pymupdf.Point(tx(obj.ll.x), ty(obj.ll.y)),
                pymupdf.Point(tx(obj.lr.x), ty(obj.lr.y))
            )
        if isinstance(obj, dict):
            return {k: transform_obj(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [transform_obj(i) for i in obj]
        return obj

    translated_draws = []
    if drawings:
        for draw in drawings:
            # Verifica se o desenho está contido ou intersecta a imagem
            if not img_bbox.intersects(draw["rect"]):
                continue
            
            # Traduz coordenadas de todos os elementos do desenho
            t_draw = transform_obj(draw)
            # Serializa para tipos básicos (listas/floats) para o JSON
            translated_draws.append(_serializar_objeto_pymupdf(t_draw))

    translated_text = []
    if text_dict and text_dict.get("blocks"):
        for block in text_dict["blocks"]:
            if block["type"] != 0: # Apenas texto
                continue
            
            # block["bbox"] em text_dict costuma ser uma tupla de floats, não Rect
            b = block["bbox"]
            b_rect = pymupdf.Rect(b)
            if not img_bbox.intersects(b_rect):
                continue
                
            t_block = dict(block)
            t_block["bbox"] = [tx(b[0]), ty(b[1]), tx(b[2]), ty(b[3])]
            t_block["lines"] = []
            
            for line in block.get("lines", []):
                t_line = dict(line)
                lb = line["bbox"]
                t_line["bbox"] = [tx(lb[0]), ty(lb[1]), tx(lb[2]), ty(lb[3])]
                t_line["spans"] = []
                for span in line.get("spans", []):
                    t_span = dict(span)
                    sb = span["bbox"]
                    t_span["bbox"] = [tx(sb[0]), ty(sb[1]), tx(sb[2]), ty(sb[3])]
                    orig = span["origin"]
                    t_span["origin"] = [tx(orig[0]), ty(orig[1])]
                    t_line["spans"].append(t_span)
                t_block["lines"].append(t_line)
            translated_text.append(t_block)

    return translated_draws, translated_text

def are_tiles(r1, r2, tolerance=1.5):
    """Verifica se dois retângulos são compatíveis como tiles (próximos e alinhados)."""
    # 1. Verifica se estão próximos ou se sobrepõem
    dx = max(0, r1.x0 - r2.x1, r2.x0 - r1.x1)
    dy = max(0, r1.y0 - r2.y1, r2.y0 - r1.y1)
    if (dx**2 + dy**2)**0.5 > tolerance:
        return False
        
    # 2. Verifica alinhamento (mesma largura ou mesma altura)
    # Tiles de fundo costumam ser tiras verticais ou horizontais perfeitas
    same_width = abs(r1.x0 - r2.x0) < tolerance and abs(r1.x1 - r2.x1) < tolerance
    same_height = abs(r1.y0 - r2.y0) < tolerance and abs(r1.y1 - r2.y1) < tolerance
    
    return same_width or same_height

def group_rects(rect_info_list, tolerance=2):
    """Agrupa retângulos que são compatíveis como tiles."""
    groups = []
    for rect, info in rect_info_list:
        merged_indices = []
        for i, group in enumerate(groups):
            # Tenta encontrar qualquer imagem no grupo que seja um "tile" compatível
            if any(are_tiles(rect, r, tolerance) for r in group['rects']):
                merged_indices.append(i)
        
        if not merged_indices:
            groups.append({
                'rects': [rect],
                'infos': [info],
                'union': rect
            })
        else:
            # Mescla com todos os grupos compatíveis
            first_idx = merged_indices[0]
            groups[first_idx]['rects'].append(rect)
            groups[first_idx]['infos'].append(info)
            groups[first_idx]['union'] = groups[first_idx]['union'] | rect
            
            # Se intersectou mais de um grupo, mescla os grupos entre si
            for other_idx in reversed(merged_indices[1:]):
                other_group = groups.pop(other_idx)
                groups[first_idx]['rects'].extend(other_group['rects'])
                groups[first_idx]['infos'].extend(other_group['infos'])
                groups[first_idx]['union'] = groups[first_idx]['union'] | other_group['union']
    return groups

def extrair_imagens_da_parte(doc, paginas, part_name, output_path, extract_full_pages=False, apenas_extrair=False):
    """Extrai imagens das páginas especificadas, agrupando tiles adjacentes por padrão."""
    raw_image_dir = output_path / "raw_imagens" / part_name
    raw_image_dir.mkdir(parents=True, exist_ok=True)

    output_image_dir = output_path / "imagens" / part_name
    output_image_dir.mkdir(parents=True, exist_ok=True)
    img_count = 0

    for local_index, page_index in enumerate(paginas):
        page = doc.load_page(page_index)
        drawings = page.get_drawings()
        text_dict = page.get_text("dict")
        
        # Matriz para converter de coordenadas do mediabox (unrotated) para página (rotated)
        trans_mat = page.rotation_matrix

        # 1. Extrair a página inteira como imagem se solicitado
        if extract_full_pages:
            pix = page.get_pixmap(dpi=150)
            page_png_path = raw_image_dir / f"p{local_index}.png"
            pix.save(str(page_png_path))
            converter_para_webp(output_image_dir, page_png_path)

        # 2. Obter informações de todas as imagens da página e agrupar tiles
        image_info = page.get_image_info()
        if not image_info:
            continue

        rect_info_list = []
        for info in image_info:
            # Converter o bbox original para o espaço de coordenadas da página (considerando rotação)
            r_unrotated = pymupdf.Rect(info["bbox"])
            r_rotated = r_unrotated * trans_mat
            rect_info_list.append((r_rotated, info))

        if apenas_extrair:
            # Com a flag habilitada, cada imagem individual é tratada separadamente (comportamento antigo)
            groups = [{'rects': [r], 'infos': [i], 'union': r} for r, i in rect_info_list]
        else:
            # Por padrão, agrupa imagens adjacentes e alinhadas (mosaicos)
            groups = group_rects(rect_info_list, tolerance=2)

        for g_idx, group in enumerate(groups):
            img_bbox = group['union']
            
            # Se o grupo for minúsculo (área quase zero), ignorar
            if img_bbox.width < 1 or img_bbox.height < 1:
                continue

            # Tenta inferir o zoom original baseado na maior largura/altura das imagens do grupo
            # para manter a resolução nativa do PDF
            max_zoom = 1.0
            for info in group['infos']:
                w_px = info.get("width", 1)
                # Usamos o bbox original para calcular o zoom pois w_px é relativo a ele
                w_pt = pymupdf.Rect(info["bbox"]).width
                if w_pt > 0:
                    max_zoom = max(max_zoom, w_px / w_pt)
            
            # Limitar zoom para evitar imagens gigantescas (max ~432 DPI)
            max_zoom = min(max_zoom, 6.0) 

            # Limitar zoom de forma dinâmica para evitar resolução insana
            if img_bbox.width > 0 and img_bbox.height > 0:
                max_width_px = img_bbox.width * max_zoom
                max_height_px = img_bbox.height * max_zoom
                if max(max_width_px, max_height_px) > 4000:
                    max_zoom = 4000.0 / max(img_bbox.width, img_bbox.height)

            # Nome base para os arquivos deste grupo
            base_name = f"p{local_index}_i{g_idx}"
            final_webp_path = output_image_dir / f"{base_name}.webp"

            # Renderizar o grupo usando o bbox rotacionado
            mat = pymupdf.Matrix(max_zoom, max_zoom)
            try:
                pix = page.get_pixmap(matrix=mat, clip=img_bbox, colorspace=pymupdf.csRGB)
            except Exception as e:
                print(f"  Erro crítico ao renderizar {base_name}: {e}. Tentando zoom menor.")
                mat = pymupdf.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat, clip=img_bbox, colorspace=pymupdf.csRGB)
            
            img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Aplicar o limite de área para o aplicativo
            max_area = 2048 * 2048
            area = img_pil.width * img_pil.height
            if area > max_area:
                scale = (max_area / area) ** 0.5
                new_width = int(img_pil.width * scale)
                new_height = int(img_pil.height * scale)
                img_pil.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Salvar WebP
            img_pil.save(final_webp_path, "WEBP", quality=85)
            
            # 3. Extrair os componentes originais (raw) deste grupo para referência
            for sub_idx, info in enumerate(group['infos']):
                xref = info.get("xref", 0)
                sub_rect_rotated = group['rects'][sub_idx]
                sub_name = f"raw_{base_name}_{sub_idx}"
                
                try:
                    if xref > 0:
                        img_data = doc.extract_image(xref)
                        if img_data:
                            ext = img_data.get("ext", "png")
                            raw_file_path = raw_image_dir / f"{sub_name}.{ext}"
                            raw_file_path.write_bytes(img_data["image"])
                    else:
                        # Se for imagem inline, renderizamos o recorte individual
                        sub_mat = pymupdf.Matrix(max_zoom, max_zoom)
                        sub_pix = page.get_pixmap(matrix=sub_mat, clip=sub_rect_rotated, colorspace=pymupdf.csRGB)
                        raw_file_path = raw_image_dir / f"{sub_name}.png"
                        sub_pix.save(str(raw_file_path))
                except Exception as e:
                    print(f"  Aviso: Erro ao extrair componente raw {sub_idx} do grupo {base_name}: {e}")

            # Gera metadados JSON para o mapa interativo
            # Traduz desenhos e blocos de texto para as coordenadas locais desta imagem
            translated_draws, translated_text = translate_coordinates(
                drawings, text_dict, img_bbox, max_zoom, img_pil.size
            )

            # Estrutura do JSON do mapa
            mapa_metadata = {
                "id": f"{part_name}_{base_name}",
                "arquivo_imagem": f"{base_name}.webp",
                "width": img_pil.size[0],
                "height": img_pil.size[1],
                "desenhos": translated_draws,
                "texto": translated_text,
                "pontos_interesse": [] # Para preenchimento manual posterior
            }

            with open(output_image_dir / f"{base_name}.json", "w", encoding="utf-8") as f:
                json.dump(mapa_metadata, f, ensure_ascii=False, indent=2)

            img_count += 1

    if img_count > 0:
        print(f"  Extraídas {img_count} imagens de '{part_name}' a partir da fonte original.")

    return doc

def repartir_pdf(pdf_path, partes_json, output_path, include_pages=False, apenas_extrair=False):
    """
    Divide o PDF original em sub-pdfs e extrai imagens.
    """
    doc_orig = pymupdf.open(pdf_path)
    _corrigir_pdf_malformado(doc_orig)

    # Cria uma cópia otimizada/corrigida para evitar problemas estruturais
    temp_pdf = output_path / "temp_corrigido.pdf"
    doc_orig.save(temp_pdf, garbage=4, deflate=True)
    doc_orig.close()

    src = pymupdf.open(temp_pdf)

    for part_name, paginas in partes_json.items():
        print(f"Processando parte: {part_name} (Páginas: {paginas})")
        
        # 1. Gerar o sub-pdf para esta parte
        new_doc = pymupdf.open()
        new_doc.insert_pdf(src, from_page=paginas[0], to_page=paginas[-1])
        
        part_pdf_path = output_path / f"{part_name}.pdf"
        new_doc.save(part_pdf_path)
        new_doc.close()
        
        # 2. Extrair imagens desta parte
        part_doc = pymupdf.open(part_pdf_path)
        extrair_imagens_da_parte(part_doc, range(len(paginas)), part_name, output_path, include_pages, apenas_extrair)
        part_doc.close()
        
        yield part_pdf_path

    src.close()
    if temp_pdf.exists():
        temp_pdf.unlink()

def main():
    parser = argparse.ArgumentParser(
        description="Quebra um PDF de escalada em vários arquivos pdfs "
        "baseado no arquivo partes.json de input e gera os metadados necessários para conversão."
    )
    
    parser.add_argument("db_folder", help="Pasta do croqui no database (ex: database/br_mg_...)")
    parser.add_argument("--incluir-paginas", action="store_true", help="Extrai também as imagens completas das páginas (pX.webp)")
    parser.add_argument("--apenas-extrair", action="store_true", help="Extrai cada componente de imagem individualmente sem agrupar mosaicos")
    args = parser.parse_args()

    db_folder = Path(args.db_folder)
    pdf_path = db_folder / "raw_original_pdf" / "croqui_original.pdf"
    partes_json_path = db_folder / "partes.json"
    output_path = db_folder / "raw_pdf_contents"

    if not db_folder.is_dir():
        print(f"Erro: Pasta '{db_folder}' não encontrada.")
        return

    if not pdf_path.exists():
        print(f"Erro: PDF original não encontrado em '{pdf_path}'.")
        return

    if not partes_json_path.exists():
        print(f"Erro: Arquivo '{partes_json_path}' não encontrado.")
        return

    if output_path.exists():
        print(f"Limpando pasta de saída: {output_path}")
        shutil.rmtree(output_path)
        
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        with open(partes_json_path, 'r', encoding='utf-8') as f:
            partes_json = json.load(f)

        for _ in repartir_pdf(pdf_path, partes_json, output_path, args.incluir_paginas, args.apenas_extrair):
            pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error processing: {e}")

if __name__ == "__main__":
    main()