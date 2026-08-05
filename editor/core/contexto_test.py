# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Aresta Contributors

import unittest
from editor.core.contexto import ContextoUIPath

class ContextoUIPathTest(unittest.TestCase):
    def test_parse_vazio(self):
        ctx = ContextoUIPath("")
        self.assertIsNone(ctx.pagina)
        self.assertEqual(ctx.caminho_local_arvore, "")
        self.assertIsNone(ctx.arquivo_mapa)

    def test_parse_none(self):
        ctx = ContextoUIPath(None)
        self.assertIsNone(ctx.pagina)
        self.assertEqual(ctx.caminho_local_arvore, "")
        self.assertIsNone(ctx.arquivo_mapa)

    def test_parse_dados(self):
        uri = "page:dados/node:root/node:Croqui/expando:Picos"
        ctx = ContextoUIPath(uri)
        self.assertEqual(ctx.pagina, "dados")
        self.assertEqual(ctx.caminho_local_arvore, "node:root/node:Croqui/expando:Picos")
        self.assertIsNone(ctx.arquivo_mapa)

    def test_parse_mapas(self):
        uri = "page:mapas/file:setor_principal.md"
        ctx = ContextoUIPath(uri)
        self.assertEqual(ctx.pagina, "mapas")
        self.assertEqual(ctx.arquivo_mapa, "setor_principal.md")
        self.assertEqual(ctx.caminho_local_arvore, "")

    def test_parse_legado(self):
        # Fallback the user said we SHOULD NOT DO, but actually we should just test how it parses
        # wait, the design says NO LEGACY COMPATIBILITY, so it's strictly the URI.
        # If there's no page: prefix, pagina is None, and the rest might just be raw.
        uri = "node:root/node:Croqui"
        ctx = ContextoUIPath(uri)
        self.assertIsNone(ctx.pagina)
        self.assertEqual(ctx.caminho_local_arvore, "node:root/node:Croqui")
        self.assertIsNone(ctx.arquivo_mapa)

if __name__ == '__main__':
    unittest.main()
