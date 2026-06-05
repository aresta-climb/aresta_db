import sys
import json
from pathlib import Path
from PIL import Image

# Adiciona o diretório raiz ao sys.path para garantir imports globais seguros
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.visualizar_mapa_processado import processar_mapa

def test_processamento_de_mapa(tmp_path):
    # Setup de arquivos faker
    img_path = tmp_path / "mapa_teste.webp"
    
    # Criar imagem falsa de fundo via PIL (200x200 branco)
    img = Image.new('RGB', (200, 200), color='white')
    img.save(img_path)
    
    # Criar JSON fictício
    json_path = tmp_path / "mapa_teste.json"
    json_data = {
        "dimensoes_mapa": {
            "canto_superior_esquerdo": {"x": 50, "y": 50},
            "largura": 100,
            "altura": 100
        },
        "pontos_de_interesse": [
            {
                "id": "1",
                "label": "Via A",
                "box": {"x": 10, "y": 10, "comprimento": 80, "largura": 80}
            }
        ]
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f)
        
    # Executa a visualização
    processar_mapa(str(img_path), str(json_path))
    
    # Verifica output (escala salva em {base_nome_json}_processado.webp)
    saida = tmp_path / "mapa_teste_processado.webp"
    assert saida.exists()
    
    # Verifica a imagem salva, as dimensões devem ser 100x100 por causa do Crop
    img_resultado = Image.open(saida)
    assert img_resultado.size == (100, 100)
    
    # Verifica se os pixels do bounding box estao vermelhos 
    # (por exemplo na borda superior, box: 10,10 a 90,90)
    # outline="red", width=3, the top edge of the rect is y=10, covering y=10,11,12 ?
    # ImageDraw in PIL draws outside/inside, mas (10,10) deve ser vermelho!
    pixel_r, pixel_g, pixel_b = img_resultado.getpixel((10, 10))
    # red in RGB = (255, 0, 0), mas webp tem compressão com perdas (lossy)
    assert pixel_r > 150
    assert pixel_g < 100
    assert pixel_b < 100
    
    # Um pixel dentro do bounding box deve continuar branco (255, 255, 255)
    pixel_in_r, pixel_in_g, pixel_in_b = img_resultado.getpixel((50, 50))
    assert pixel_in_r > 200
    assert pixel_in_g > 200
    assert pixel_in_b > 200
