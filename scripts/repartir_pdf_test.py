import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY

# Adiciona o diretório raiz ao sys.path para importação de build e scripts relativos
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.repartir_pdf import repartir_pdf, extrair_imagens_da_parte, converter_para_webp, group_rects

def test_converter_para_webp(tmp_path):
    imagem_origem = tmp_path / "teste.png"
    imagem_origem.write_bytes(b"dummy")
    pasta_destino = tmp_path / "imagens"
    pasta_destino.mkdir()
    
    with patch("scripts.repartir_pdf.Image.open") as mock_pil_open:
        mock_pil = MagicMock()
        mock_pil.size = (1000, 800)
        mock_pil_open.return_value.__enter__.return_value = mock_pil
        
        converter_para_webp(pasta_destino, imagem_origem)
        
        mock_pil_open.assert_called_once_with(imagem_origem)
        mock_pil.save.assert_called_once()
        args, kwargs = mock_pil.save.call_args
        assert args[0] == pasta_destino / "teste.webp"
        assert args[1] == "WEBP"
        assert kwargs["quality"] == 85


def test_corrigir_pdf_malformado():
    from scripts.repartir_pdf import _corrigir_pdf_malformado
    
    mock_doc = MagicMock()
    mock_doc.pdf_catalog.return_value = 100
    
    _corrigir_pdf_malformado(mock_doc)
    
    # Verifica se buscou o catálogo e tentou setar a StructTreeRoot para null
    mock_doc.pdf_catalog.assert_called_once()
    mock_doc.xref_set_key.assert_called_once_with(100, "StructTreeRoot", "null")


def test_reparticao_de_pdf(tmp_path):
    # Cria os recursos fake
    pdf_path = tmp_path / "dummy.pdf"
    pdf_path.write_bytes(b"dummy pdf bytes")
    
    output_path = tmp_path / "output"
    output_path.mkdir()
    
    partes_json = {
        "setor_a": [0],
        "setor_b": [1, 2]
    }
    
    with patch("scripts.repartir_pdf.pymupdf.open") as mock_open, \
         patch("scripts.repartir_pdf.extrair_imagens_da_parte") as mock_extrair:
        mock_src_orig = MagicMock()
        mock_src_opt = MagicMock()
        mock_new_doc = MagicMock()
        
        # mock_open(pdf_path) -> doc_orig
        # mock_open(temp_pdf) -> src
        # mock_open() -> new_doc (2x)
        # mock_open(part_pdf_path) -> part_doc (2x)
        mock_open.side_effect = [mock_src_orig, mock_src_opt, mock_new_doc, mock_src_opt, mock_new_doc, mock_src_opt]
        
        # Consome o gerador
        resultados = list(repartir_pdf(pdf_path, partes_json, output_path))
        
        assert len(resultados) == 2
        # Verifica se chamou a extração para cada parte
        assert mock_extrair.call_count == 2

def test_main_cleanup(tmp_path):
    from scripts.repartir_pdf import main
    db_folder = tmp_path / "db"
    db_folder.mkdir()
    pdf_dir = db_folder / "raw_original_pdf"
    pdf_dir.mkdir()
    (pdf_dir / "croqui_original.pdf").write_bytes(b"pdf")
    (db_folder / "partes.json").write_text('{"a": [0]}')
    
    output_path = db_folder / "raw_pdf_contents"
    output_path.mkdir()
    (output_path / "stale.txt").write_text("stale")

    with patch("sys.argv", ["repartir_pdf.py", str(db_folder)]), \
         patch("scripts.repartir_pdf.repartir_pdf", return_value=iter([])), \
         patch("scripts.repartir_pdf.shutil.rmtree") as mock_rmtree:
        
        main()
        
        # Verifica se tentou remover a pasta existente
        mock_rmtree.assert_called_once_with(output_path)

def test_group_rects():
    import pymupdf
    
    # 1. Caso Tiling: Imagens adjacentes e ALINHADAS devem agrupar
    r1 = pymupdf.Rect(0, 0, 100, 100)
    r2 = pymupdf.Rect(101, 0, 200, 100) # Mesma altura, deve agrupar
    r3 = pymupdf.Rect(0, 101, 100, 200) # Mesma largura, deve agrupar
    
    infos = [(r1, {"id": 1}), (r2, {"id": 2}), (r3, {"id": 3})]
    groups = group_rects(infos, tolerance=5)
    assert len(groups) == 1
    
    # 2. Caso Separado por Distância: Não devem agrupar
    r4 = pymupdf.Rect(500, 500, 600, 600)
    infos.append((r4, {"id": 4}))
    groups = group_rects(infos, tolerance=5)
    assert len(groups) == 2
    
    # 3. Caso DESALINHADO: Imagens que tocam mas não compartilham largura/altura
    r5 = pymupdf.Rect(0, 0, 1000, 1000) # Background grande
    r6 = pymupdf.Rect(200, 200, 400, 400) # Foto no meio
    
    infos_desalinhados = [(r5, {"id": 5}), (r6, {"id": 6})]
    groups_refined = group_rects(infos_desalinhados, tolerance=5)
    assert len(groups_refined) == 2 

def test_extrair_imagens_agrupamento(tmp_path):
    import pymupdf
    output_path = tmp_path / "output_group"
    
    with patch("scripts.repartir_pdf.Image.frombytes") as mock_frombytes, \
         patch("scripts.repartir_pdf.Image.open") as mock_open_pil:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_page.rotation_matrix = pymupdf.Matrix(1.0, 1.0)
        
        # Simula 2 imagens próximas (tiles) alinhadas com XREFs
        mock_page.get_image_info.return_value = [
            {"bbox": (0, 0, 100, 100), "width": 500, "height": 500, "xref": 10},
            {"bbox": (100, 0, 200, 100), "width": 500, "height": 500, "xref": 11}
        ]
        
        mock_pix = MagicMock()
        mock_pix.width = 1000
        mock_pix.height = 500
        mock_pix.samples = b"..."
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pil = MagicMock()
        mock_pil.size = (1000, 500)
        def mock_save(path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"fake_webp")
        mock_pil.save.side_effect = mock_save
        mock_pil.convert.return_value = mock_pil

        mock_frombytes.return_value = mock_pil
        mock_frombytes.return_value.__enter__.return_value = mock_pil
        mock_open_pil.return_value.__enter__.return_value = mock_pil
        
        mock_doc.extract_image.return_value = {"image": b"fake", "ext": "png"}
        
        extrair_imagens_da_parte(mock_doc, [0], "setor_a", output_path)
        
        # Deve ter chamado get_pixmap para o grupo unido
        assert mock_page.get_pixmap.call_count >= 1
        
        # Deve ter criado os arquivos raw dos componentes (agora sempre WebP)
        assert (output_path / "raw_imagens" / "setor_a" / "raw_p0_i0_0.webp").exists()
        assert (output_path / "raw_imagens" / "setor_a" / "raw_p0_i0_1.webp").exists()

def test_apenas_extrair(tmp_path):
    import pymupdf
    output_path = tmp_path / "output_raw"
    
    with patch("scripts.repartir_pdf.Image.frombytes") as mock_frombytes, \
         patch("scripts.repartir_pdf.Image.open") as mock_open_pil:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_page.rotation_matrix = pymupdf.Matrix(1.0, 1.0)
        
        # Simula 2 imagens próximas que seriam agrupadas
        mock_page.get_image_info.return_value = [
            {"bbox": (0, 0, 100, 100), "width": 500, "height": 500, "xref": 20},
            {"bbox": (100, 0, 200, 100), "width": 500, "height": 500, "xref": 21}
        ]
        
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pil = MagicMock()
        mock_pil.size = (500, 500)
        def mock_save(path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"fake_webp")
        mock_pil.save.side_effect = mock_save
        mock_pil.convert.return_value = mock_pil

        mock_frombytes.return_value = mock_pil
        mock_frombytes.return_value.__enter__.return_value = mock_pil
        mock_open_pil.return_value.__enter__.return_value = mock_pil
        
        # Chama com apenas_extrair=True
        extrair_imagens_da_parte(mock_doc, [0], "setor_a", output_path, apenas_extrair=True)
        
        # Deve ter chamado get_pixmap 2 VEZES (NÃO agrupou)
        assert mock_page.get_pixmap.call_count == 2

def test_limite_resolucao_2048(tmp_path):
    import pymupdf
    output_path = tmp_path / "output_limit"
    
    with patch("scripts.repartir_pdf.Image.frombytes") as mock_frombytes, \
         patch("scripts.repartir_pdf.Image.open") as mock_open_pil:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_page.rotation_matrix = pymupdf.Matrix(1.0, 1.0)
        mock_page.get_image_info.return_value = [{"bbox": (0, 0, 100, 100), "width": 3000, "height": 3000, "xref": 40}]
        
        mock_pix = MagicMock()
        mock_pix.width = 3000
        mock_pix.height = 3000
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pil = MagicMock()
        mock_pil.size = (3000, 3000)
        def mock_save(path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"fake_webp")
        mock_pil.save.side_effect = mock_save
        mock_pil.convert.return_value = mock_pil

        mock_frombytes.return_value = mock_pil
        mock_frombytes.return_value.__enter__.return_value = mock_pil
        mock_open_pil.return_value.__enter__.return_value = mock_pil
        
        extrair_imagens_da_parte(mock_doc, [0], "setor_a", output_path)
        
        # Deve ter chamado thumbnail para redimensionar para 2048
        mock_pil.thumbnail.assert_called_once()
        args = mock_pil.thumbnail.call_args[0]
        assert args[0] == (2048, 2048)

def test_extrair_imagens_da_parte_base(tmp_path):
    import pymupdf
    output_path = tmp_path / "output_base"
    
    with patch("scripts.repartir_pdf.Image.frombytes") as mock_frombytes, \
         patch("scripts.repartir_pdf.Image.open") as mock_open_pil, \
         patch("scripts.repartir_pdf.converter_para_webp"):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_page.rotation_matrix = pymupdf.Matrix(1.0, 1.0)
        
        mock_page.get_image_info.return_value = [{"bbox": (10, 10, 110, 110), "width": 100, "height": 100, "xref": 30}]
        
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pil = MagicMock()
        mock_pil.size = (100, 100)
        def mock_save(path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"fake_webp")
        mock_pil.save.side_effect = mock_save
        mock_pil.convert.return_value = mock_pil

        mock_frombytes.return_value = mock_pil
        mock_frombytes.return_value.__enter__.return_value = mock_pil
        mock_open_pil.return_value.__enter__.return_value = mock_pil
        
        extrair_imagens_da_parte(mock_doc, [0], "setor_a", output_path, extract_full_pages=True)
        
        # Chamou get_pixmap 2 vezes: 1 para a página inteira, 1 para a imagem
        assert mock_page.get_pixmap.call_count == 2

def test_extrair_componentes_raw(tmp_path):
    import pymupdf
    output_path = tmp_path / "output_raw_test"
    
    with patch("scripts.repartir_pdf.Image.frombytes") as mock_frombytes, \
         patch("scripts.repartir_pdf.Image.open") as mock_open_pil:
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_doc.load_page.return_value = mock_page
        mock_page.rotation_matrix = pymupdf.Matrix(1.0, 1.0)
        
        # Simula 2 componentes: um com XREF (mosaico normal) e um sem XREF (inline)
        mock_page.get_image_info.return_value = [
            {"bbox": (0, 0, 100, 100), "width": 500, "height": 500, "xref": 100}, # XREF
            {"bbox": (100, 0, 200, 100), "width": 500, "height": 500}             # Inline (sem xref)
        ]
        
        # Mock para o pixmap individual (inline)
        mock_pix = MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pil = MagicMock()
        mock_pil.size = (1000, 500)
        
        def mock_save(path, *args, **kwargs):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"fake_webp")
        mock_pil.save.side_effect = mock_save
        mock_pil.convert.return_value = mock_pil

        # Configura o mock para funcionar tanto com 'with' quanto sem
        mock_frombytes.return_value = mock_pil
        mock_frombytes.return_value.__enter__.return_value = mock_pil
        mock_open_pil.return_value.__enter__.return_value = mock_pil
        
        # Mock para extração de imagem binária
        mock_doc.extract_image.return_value = {"image": b"fake_binary", "ext": "jpeg"}
        
        extrair_imagens_da_parte(mock_doc, [0], "setor_a", output_path)
        
        # 1. Verifica se o componente com XREF foi salvo como .webp
        raw_xref_path = output_path / "raw_imagens" / "setor_a" / "raw_p0_i0_0.webp"
        assert raw_xref_path.exists()
        
        # 2. Verifica se o componente inline foi salvo como .webp
        raw_inline_path = output_path / "raw_imagens" / "setor_a" / "raw_p0_i0_1.webp"
        assert raw_inline_path.exists()
        
        # Ambas as chamadas de save devem ter acontecido
        assert mock_pil.save.call_count >= 2

def test_serializar_objeto_pymupdf_quad():
    import pymupdf
    from scripts.repartir_pdf import _serializar_objeto_pymupdf
    
    quad = pymupdf.Quad(pymupdf.Point(0, 0), pymupdf.Point(10, 0), pymupdf.Point(0, 10), pymupdf.Point(10, 10))
    res = _serializar_objeto_pymupdf(quad)
    assert res == [[0.0, 0.0], [10.0, 0.0], [0.0, 10.0], [10.0, 10.0]]

def test_translate_coordinates_quad():
    import pymupdf
    from scripts.repartir_pdf import translate_coordinates
    
    quad = pymupdf.Quad(pymupdf.Point(10, 10), pymupdf.Point(20, 10), pymupdf.Point(10, 20), pymupdf.Point(20, 20))
    drawings = [{"rect": pymupdf.Rect(0, 0, 100, 100), "items": [("qu", quad)]}]
    img_bbox = pymupdf.Rect(0, 0, 50, 50)
    zoom = 1.0
    img_size_px = (100, 100) # scale will be 2.0
    
    translated_draws, translated_text = translate_coordinates(drawings, None, img_bbox, zoom, img_size_px)
    
    assert len(translated_draws) == 1
    items = translated_draws[0]["items"]
    assert items[0][0] == "qu"
    quad_list = items[0][1]
    
    # Scale is 2.0, origin is (0,0), so (10,10) -> (20,20)
    assert quad_list == [[20.0, 20.0], [40.0, 20.0], [20.0, 40.0], [40.0, 40.0]]
