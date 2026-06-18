import unittest
import io
from PIL import Image
from pathlib import Path
import tempfile
import os

from scripts.comprimir_imagens import comprimir_imagem_para_bytes, comprimir_imagem

class TestComprimirImagens(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for file tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def criar_imagem_teste(self, width, height, color="red"):
        img = Image.new('RGB', (width, height), color=color)
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    def test_comprimir_imagem_para_bytes_diminui_area(self):
        # Imagem maior que max_area 100x100 = 10000
        img_bytes = self.criar_imagem_teste(200, 200) # Area = 40000
        
        # Comprimir com max_area 10000 (100x100)
        resultado, final_w, final_h = comprimir_imagem_para_bytes(img_bytes, quality=80, max_area=10000)
        
        self.assertIsNotNone(resultado)
        self.assertIsInstance(resultado, bytes)
        
        # Verificar o tamanho usando PIL
        with Image.open(io.BytesIO(resultado)) as final_img:
            self.assertEqual(final_img.format, "WEBP")
            area = final_img.width * final_img.height
            self.assertLessEqual(area, 10000)
            self.assertEqual(final_w, final_img.width)
            self.assertEqual(final_h, final_img.height)
            
            # Since aspect ratio is 1:1, it should be exactly 100x100
            self.assertEqual(final_img.width, 100)
            self.assertEqual(final_img.height, 100)

    def test_comprimir_imagem_para_bytes_mantem_formato_se_menor(self):
        # Imagem menor que a area maxima
        img_bytes = self.criar_imagem_teste(50, 50)
        
        # Comprimir
        resultado, final_w, final_h = comprimir_imagem_para_bytes(img_bytes, quality=80, max_area=10000)
        
        # Deve converter para WEBP de qualquer forma
        self.assertIsNotNone(resultado)
        with Image.open(io.BytesIO(resultado)) as final_img:
            self.assertEqual(final_img.format, "WEBP")
            self.assertEqual(final_img.width, 50)
            self.assertEqual(final_img.height, 50)

    def test_comprimir_imagem_para_bytes_ja_eh_webp_pequeno(self):
        # Se for um webp menor que o limite, talvez possamos retornar os mesmos bytes?
        # A especificacao nao fala se converte webp pequeno de volta para webp.
        # Vamos assumir que sempre processa, pois a UI precisa ler os bytes como webp.
        pass

    def test_comprimir_imagem_substitui_arquivo(self):
        # Criar imagem local de 200x200 (area 40000)
        file_path = self.test_dir_path / "teste.jpg"
        with open(file_path, 'wb') as f:
            f.write(self.criar_imagem_teste(200, 200))
            
        # Comprimir para max_area 10000
        teve_alteracao = comprimir_imagem(file_path, quality=80, max_area=10000)
        
        self.assertTrue(teve_alteracao)
        self.assertTrue(file_path.exists())
        
        with Image.open(file_path) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertEqual(img.width, 100)
            self.assertEqual(img.height, 100)

if __name__ == '__main__':
    unittest.main()
