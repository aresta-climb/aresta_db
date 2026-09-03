# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
import tempfile
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from scripts.calcular_tamanho_croqui_lib import calcular_tamanho_croqui_bytes


class CalcularTamanhoCroquiLibTest(unittest.TestCase):
    def test_calcular_tamanho_croqui_completo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            compilado_pb = base_dir / 'compilado.binarypb'
            compilado_pb.write_bytes(b'x' * 500)

            imagens_dir = base_dir / 'imagens'
            imagens_dir.mkdir()
            (imagens_dir / 'foto1.webp').write_bytes(b'a' * 200)
            (imagens_dir / 'foto2.webp').write_bytes(b'b' * 300)

            # Subpasta excluida (padrao raw_mapas)
            raw_dir = imagens_dir / 'raw_mapas'
            raw_dir.mkdir()
            (raw_dir / 'rascunho.png').write_bytes(b'c' * 1000)

            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=compilado_pb,
                pasta_imagens=imagens_dir,
                pastas_excluidas={'raw_mapas'}
            )
            # 500 + 200 + 300 = 1000
            self.assertEqual(tamanho, 1000)

    def test_calcular_tamanho_sem_pasta_imagens(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            compilado_pb = base_dir / 'compilado.binarypb'
            compilado_pb.write_bytes(b'x' * 400)

            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=compilado_pb,
                pasta_imagens=None
            )
            self.assertEqual(tamanho, 400)

    def test_calcular_tamanho_pasta_imagens_inexistente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            compilado_pb = base_dir / 'compilado.binarypb'
            compilado_pb.write_bytes(b'x' * 400)

            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=compilado_pb,
                pasta_imagens=base_dir / 'imagens_inexistente'
            )
            self.assertEqual(tamanho, 400)

    def test_calcular_tamanho_compilado_inexistente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            compilado_inexistente = base_dir / 'compilado.binarypb'

            imagens_dir = base_dir / 'imagens'
            imagens_dir.mkdir()
            (imagens_dir / 'foto1.webp').write_bytes(b'a' * 300)

            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=compilado_inexistente,
                pasta_imagens=imagens_dir
            )
            self.assertEqual(tamanho, 300)

    def test_calcular_tamanho_tudo_inexistente(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=base_dir / 'compilado.binarypb',
                pasta_imagens=base_dir / 'imagens'
            )
            self.assertEqual(tamanho, 0)

    def test_calcular_tamanho_pastas_excluidas_customizadas(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            imagens_dir = base_dir / 'imagens'
            imagens_dir.mkdir()
            (imagens_dir / 'foto_raiz.webp').write_bytes(b'a' * 100)

            temp_dir = imagens_dir / 'temp'
            temp_dir.mkdir()
            (temp_dir / 'temp.webp').write_bytes(b'b' * 500)

            sub_dir = imagens_dir / 'setor1'
            sub_dir.mkdir()
            (sub_dir / 'foto_setor.webp').write_bytes(b'c' * 200)

            tamanho = calcular_tamanho_croqui_bytes(
                caminho_compilado=base_dir / 'compilado.binarypb',
                pasta_imagens=imagens_dir,
                pastas_excluidas={'temp'}
            )
            # 100 + 200 = 300
            self.assertEqual(tamanho, 300)


if __name__ == '__main__':
    unittest.main()
