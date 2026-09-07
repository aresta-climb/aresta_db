# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image


class TestManifestoMsixBeta(unittest.TestCase):
    def setUp(self) -> None:
        self.raiz_projeto = Path(__file__).resolve().parent.parent
        self.manifesto_path = self.raiz_projeto / "editor" / "msix_beta" / "AppxManifest.xml"
        self.assets_dir = self.raiz_projeto / "editor" / "msix_beta" / "Assets"

    def test_manifesto_msix_beta_possui_background_color_azul(self) -> None:
        """Garante que o BackgroundColor do canal Beta seja #4197EA para evitar bordas com cor de destaque do Windows."""
        self.assertTrue(self.manifesto_path.exists())
        arvore = ET.parse(self.manifesto_path)
        raiz = arvore.getroot()
        ns = {
            "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
        }
        visual_elements = raiz.find(".//uap:VisualElements", ns)
        self.assertIsNotNone(visual_elements)
        assert visual_elements is not None
        cor_fundo = visual_elements.attrib.get("BackgroundColor", "")
        self.assertEqual(cor_fundo.upper(), "#4197EA")

    def test_square150x150_logo_sem_margens_transparentes(self) -> None:
        """Garante que a imagem Square150x150Logo.png seja 100% opaca (sem margens transparentes)."""
        logo_path = self.assets_dir / "Square150x150Logo.png"
        self.assertTrue(logo_path.exists())
        im = Image.open(logo_path).convert("RGBA")
        self.assertEqual(im.size, (150, 150))
        pixel_borda = im.getpixel((0, 0))
        self.assertEqual(pixel_borda[3], 255, "A borda não pode ser transparente")
        self.assertEqual((pixel_borda[0], pixel_borda[1], pixel_borda[2]), (65, 151, 234))

    def test_manifesto_msix_beta_possui_arquitetura_x64(self) -> None:
        """Garante que a tag Identity declare ProcessorArchitecture='x64' em conformidade com o AppInstaller."""
        self.assertTrue(self.manifesto_path.exists())
        arvore = ET.parse(self.manifesto_path)
        raiz = arvore.getroot()
        ns = {
            "m": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
        }
        identity = raiz.find(".//m:Identity", ns)
        if identity is None:
            identity = raiz.find("Identity")
        self.assertIsNotNone(identity)
        assert identity is not None
        arch = identity.attrib.get("ProcessorArchitecture", "")
        self.assertEqual(arch.lower(), "x64", "Identity deve declarar ProcessorArchitecture='x64' para coincidir com o AppInstaller")

