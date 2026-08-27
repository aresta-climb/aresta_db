# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para o script de exportação Anchor Ledge.
Seguindo TDD: Os testes falham inicialmente pois a implementação ainda não existe.
"""
import unittest
from unittest.mock import MagicMock, patch
import exportar_para_anchor_ledge

class TestExportarParaAnchorLedge(unittest.TestCase):

    def test_converter_graduacao_br_6sup(self):
        """Testa se a conversão do grau inteiro para string BR funciona corretamente."""
        # Supondo que 13 seja o ID do BR_6SUP no proto (apenas um exemplo no teste)
        # O mock do proto vai simular que o enum 13 chama-se BR_6SUP.
        mock_enum_descriptor = MagicMock()
        mock_value = MagicMock()
        mock_value.name = 'BR_6SUP'
        mock_enum_descriptor.values_by_number = {13: mock_value}
        
        resultado = exportar_para_anchor_ledge.converter_graduacao(13, mock_enum_descriptor)
        self.assertEqual(resultado, '6sup')

    def test_converter_graduacao_br_8a_barra_8b(self):
        """Testa conversão com barra."""
        mock_enum_descriptor = MagicMock()
        mock_value = MagicMock()
        mock_value.name = 'BR_8A_BARRA_8B'
        mock_enum_descriptor.values_by_number = {50: mock_value}
        
        resultado = exportar_para_anchor_ledge.converter_graduacao(50, mock_enum_descriptor)
        self.assertEqual(resultado, '8a/8b')
        
    def test_converter_graduacao_desconhecida(self):
        """Testa o comportamento com uma graduação não mapeada ou sem prefixo BR."""
        mock_enum_descriptor = MagicMock()
        mock_value = MagicMock()
        mock_value.name = 'OUTRO_TIPO'
        mock_enum_descriptor.values_by_number = {99: mock_value}
        
        resultado = exportar_para_anchor_ledge.converter_graduacao(99, mock_enum_descriptor)
        self.assertEqual(resultado, '')
        
    def test_extrair_ano_abertura(self):
        """Testa a extração do ano da data de abertura (formato YYYY...)."""
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_abertura('1994'), '1994')
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_abertura('1994-06'), '1994')
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_abertura('1994-06-30'), '1994')
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_abertura(''), '')
        
    def test_extrair_ano_manutencao(self):
        """Testa a extração do ano da data de manutenção (formato DD/MM/YYYY)."""
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_manutencao('27/05/2022'), '2022')
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_manutencao('04/07/2026'), '2026')
        self.assertEqual(exportar_para_anchor_ledge.extrair_ano_manutencao(''), '')
        
    def test_mapear_estrelas(self):
        """Testa o mapeamento de estrelas baseado no campo destaque."""
        self.assertEqual(exportar_para_anchor_ledge.mapear_estrelas(True), '3')
        self.assertEqual(exportar_para_anchor_ledge.mapear_estrelas(False), '0')

    def test_determinar_status_e_material(self):
        """Testa o preenchimento de status e material baseado no tipo da via."""
        # Via esportiva
        status, mat = exportar_para_anchor_ledge.determinar_status_e_material('via_esportiva')
        self.assertEqual(status, 'OPEN')
        self.assertEqual(mat, 'UNKNOWN')
        
        # Via movel
        status, mat = exportar_para_anchor_ledge.determinar_status_e_material('via_movel')
        self.assertEqual(status, 'OPEN')
        self.assertEqual(mat, 'TRAD')
        
        # Projeto
        status, mat = exportar_para_anchor_ledge.determinar_status_e_material('projeto')
        self.assertEqual(status, 'CLOSED')
        self.assertEqual(mat, '')

if __name__ == '__main__':
    unittest.main()
