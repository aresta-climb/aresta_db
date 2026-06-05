import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np

# Adiciona o diretório raiz ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.preparar_extracao_de_mapas import PreparadorDeMapas

def test_processamento_de_md_com_mapas(tmp_path):
    # Setup de arquivos faker
    pico_path = tmp_path / "pico_teste"
    pico_path.mkdir()
    
    img_dir = pico_path / "imagens"
    img_dir.mkdir()
    
    img_path = img_dir / "mapa1.webp"
    # Cria uma imagem real mínima para o PIL e numpy não quebrarem
    img = Image.new('RGB', (100, 100), color='black')
    img.save(img_path)
    
    md_file = pico_path / "setor_teste.md"
    md_content = """---
mapas:
- caminho_imagem_mapa: imagens/mapa1.webp
---
Conteudo!
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    # Executa o Preparador com OCR mockado
    with patch("scripts.preparar_extracao_de_mapas.PaddleOCR") as MockOCR:
        # Configura o mock do OCR
        mock_engine = MagicMock()
        MockOCR.return_value = mock_engine
        
        # Simula o retorno de predict()
        mock_result = MagicMock()
        mock_result.get.side_effect = lambda key, default=None: {
            "rec_texts": ["Via A"],
            "rec_boxes": [[10, 10, 50, 50]] # bbox ficticio
        }.get(key, default)
        
        mock_engine.predict.return_value = [mock_result]
        
        # Roda o código real
        preparador = PreparadorDeMapas(idioma="pt")
        preparador.executar(pico_path)
        
        # Verifica se o JSON inicial do mapa foi criado
        raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
        mapa_json = raw_mapas_dir / "mapa1.json"
        assert mapa_json.exists()
        
        with open(mapa_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
            assert dados["caminho_imagem_mapa"] == "imagens/mapa1.webp"
            assert dados["dimensoes_imagem"] == {"largura": 100, "altura": 100}
            
        # Verifica se o JSON de resultado OCR foi criado
        ocr_json = raw_mapas_dir / "mapa1.ocr_result.json"
        assert ocr_json.exists()
        
        with open(ocr_json, "r", encoding="utf-8") as f:
            ocr_dados = json.load(f)
            assert len(ocr_dados["ocr_result"]) == 1
            assert ocr_dados["ocr_result"][0]["text"] == "Via A"
            assert ocr_dados["ocr_result"][0]["box"]["x"] == 30
            assert ocr_dados["ocr_result"][0]["box"]["y"] == 30
            assert ocr_dados["ocr_result"][0]["box"]["comprimento"] == 40
            assert ocr_dados["ocr_result"][0]["box"]["largura"] == 40
            # Ângulo zero -> omitido
            assert "angulo_graus_x100" not in ocr_dados["ocr_result"][0]["box"]
            
        # Verifica salvamento da imagem ocr_result.png
        mock_result.save_to_img.assert_called_once()

def test_processamento_obliquo(tmp_path):
    pico_path = tmp_path / "pico_obliquo"
    pico_path.mkdir()
    img_dir = pico_path / "imagens"
    img_dir.mkdir()
    img_path = img_dir / "mapa_obliquo.webp"
    Image.new('RGB', (100, 100), color='black').save(img_path)
    
    md_file = pico_path / "setor_obliquo.md"
    md_file.write_text("---\nmapas:\n- caminho_imagem_mapa: imagens/mapa_obliquo.webp\n---\n", encoding="utf-8")
    
    with patch("scripts.preparar_extracao_de_mapas.PaddleOCR") as MockOCR:
        mock_engine = MagicMock()
        MockOCR.return_value = mock_engine
        
        mock_result = MagicMock()
        # Box rotacionado 45 graus: Centro (10, 20), Lado ~14.14
        box_obliquo = [[10, 10], [20, 20], [10, 30], [0, 20]]
        mock_result.get.side_effect = lambda key, default=None: {
            "rec_texts": ["Inclinado"],
            "rec_boxes": [np.array(box_obliquo)],
            "rec_polys": [np.array(box_obliquo)]
        }.get(key, default)
        
        mock_engine.predict.return_value = [mock_result]
        
        preparador = PreparadorDeMapas(idioma="pt")
        preparador.executar(pico_path)
        
        ocr_json = pico_path / "imagens" / "raw_mapas" / "mapa_obliquo.ocr_result.json"
        with open(ocr_json, "r", encoding="utf-8") as f:
            ocr_dados = json.load(f)
            box = ocr_dados["ocr_result"][0]["box"]
            assert box["x"] == 10
            assert box["y"] == 20
            assert box["comprimento"] == 14
            assert box["largura"] == 14
            assert box["angulo_graus_x100"] == 4500

def test_md_sem_mapas(tmp_path):
    pico_path = tmp_path / "pico_sem_mapas"
    pico_path.mkdir()
    md_file = pico_path / "setor_sem_mapas.md"
    md_file.write_text("---\noutro_campo: valor\n---\n", encoding="utf-8")
    
    with patch("scripts.preparar_extracao_de_mapas.PaddleOCR"):
        preparador = PreparadorDeMapas(idioma="pt")
        preparador.executar(pico_path)
        
        # A pasta raw_mapas é criada sempre, mas deve estar vazia (sem JSONs para este arquivo)
        raw_mapas_dir = pico_path / "imagens" / "raw_mapas"
        assert raw_mapas_dir.exists()
        jsons = list(raw_mapas_dir.glob("*.json"))
        assert len(jsons) == 0

def test_processamento_com_erros_ocr(tmp_path):
    pico_path = tmp_path / "pico_erro_ocr"
    pico_path.mkdir()
    img_dir = pico_path / "imagens"
    img_dir.mkdir()
    img_path = img_dir / "mapa_erro.webp"
    Image.new('RGB', (100, 100)).save(img_path)
    
    md_file = pico_path / "setor_erro.md"
    md_file.write_text("---\nmapas:\n- caminho_imagem_mapa: imagens/mapa_erro.webp\n---\n", encoding="utf-8")
    
    with patch("scripts.preparar_extracao_de_mapas.PaddleOCR") as MockOCR:
        mock_engine = MagicMock()
        MockOCR.return_value = mock_engine
        
        mock_result = MagicMock()
        # Simular vários tipos de erro no formato do box
        mock_result.get.side_effect = lambda key, default=None: {
            "rec_texts": ["Bom", "Erro Len", "Erro Tipo", "Erro Fatal"],
            "rec_boxes": [
                [0, 0, 10, 10],   # Bom
                [0, 0, 10],       # Erro Len (3 elementos) -> cai no 'else' -> unpack falha -> try-except pega
                "nao_eh_lista",   # Erro Tipo -> fallback len falha -> try-except pega
                [0, 0, 0]         # Erro Fatal (muito curto)
            ],
            "rec_polys": [
                None,             # Bom (usa fallback)
                None,
                None,
                None
            ]
        }.get(key, default)
        
        mock_engine.predict.return_value = [mock_result]
        
        preparador = PreparadorDeMapas(idioma="pt")
        preparador.executar(pico_path)
        
        ocr_json = pico_path / "imagens" / "raw_mapas" / "mapa_erro.ocr_result.json"
        with open(ocr_json, "r", encoding="utf-8") as f:
            ocr_dados = json.load(f)
            # Apenas o primeiro ("Bom") deve ter sido processado com sucesso
            assert len(ocr_dados["ocr_result"]) == 1
            assert ocr_dados["ocr_result"][0]["text"] == "Bom"

def test_preservacao_de_pontos_existentes(tmp_path):
    pico_path = tmp_path / "pico_pontos"
    pico_path.mkdir()
    img_dir = pico_path / "imagens"
    img_dir.mkdir()
    img_path = img_dir / "mapa_com_pontos.webp"
    Image.new('RGB', (100, 100)).save(img_path)
    
    md_file = pico_path / "setor_pontos.md"
    md_content = """---
mapas:
- caminho_imagem_mapa: imagens/mapa_com_pontos.webp
  pontos_de_interesse:
  - id: via1
    label: Via 1
    box:
      x: 50
      y: 50
      comprimento: 10
      largura: 10
---
"""
    md_file.write_text(md_content, encoding="utf-8")
    
    with patch("scripts.preparar_extracao_de_mapas.PaddleOCR") as MockOCR:
        mock_engine = MagicMock()
        MockOCR.return_value = mock_engine
        mock_engine.predict.return_value = [MagicMock()] # Resultado vazio para ignorar OCR
        
        preparador = PreparadorDeMapas(idioma="pt")
        preparador.executar(pico_path)
        
        target_json = pico_path / "imagens" / "raw_mapas" / "mapa_com_pontos.json"
        assert target_json.exists()
        
        with open(target_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
            assert len(dados["pontos_de_interesse"]) == 1
            assert dados["pontos_de_interesse"][0]["id"] == "via1"
            assert dados["pontos_de_interesse"][0]["label"] == "Via 1"

