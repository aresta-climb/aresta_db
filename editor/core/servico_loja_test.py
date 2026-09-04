# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import unittest
from unittest.mock import MagicMock, patch
from editor.core.servico_loja import (
    ServicoLoja, 
    StatusAtualizacao, 
    ResultadoAtualizacao,
    obter_pacote_atual,
    obter_contexto_loja
)

class TestServicoLoja(unittest.TestCase):
    """Testes unitários para o ServicoLoja (TDD - 100% Cobertura)."""

    def setUp(self):
        self.servico = ServicoLoja(id_produto="fake_product_id")

    def test_id_produto_padrao_oficial(self):
        """Deve utilizar o Store ID oficial 9N6CQNH78WN8 por padrão."""
        servico_padrao = ServicoLoja()
        self.assertEqual(servico_padrao.id_produto, "9N6CQNH78WN8")
        self.assertEqual(ServicoLoja.ID_PRODUTO_PADRAO, "9N6CQNH78WN8")

    def test_obter_pacote_atual_sucesso(self):
        """Testa obter_pacote_atual quando winrt está disponível no Windows."""
        mock_winrt_package = MagicMock()
        mock_winrt_package.current = MagicMock()
        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"winrt.windows.applicationmodel": MagicMock(Package=mock_winrt_package)}):
                pacote = obter_pacote_atual()
                self.assertEqual(pacote, mock_winrt_package.current)

    def test_obter_pacote_atual_em_plataforma_nao_windows(self):
        """Testa obter_pacote_atual quando executado no Linux/macOS."""
        with patch("sys.platform", "linux"):
            with self.assertRaises(OSError):
                obter_pacote_atual()

    def test_obter_pacote_atual_falha(self):
        """Testa obter_pacote_atual quando winrt falha no Windows."""
        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"winrt.windows.applicationmodel": None}):
                with self.assertRaises(OSError):
                    obter_pacote_atual()

    def test_obter_contexto_loja_sucesso(self):
        """Testa obter_contexto_loja quando winrt está disponível no Windows."""
        mock_store = MagicMock()
        mock_store.get_default.return_value = MagicMock()
        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"winrt.windows.services.store": MagicMock(StoreContext=mock_store)}):
                contexto = obter_contexto_loja()
                self.assertIsNotNone(contexto)

    def test_obter_contexto_loja_em_plataforma_nao_windows(self):
        """Testa obter_contexto_loja quando executado no Linux/macOS."""
        with patch("sys.platform", "linux"):
            with self.assertRaises(OSError):
                obter_contexto_loja()

    def test_obter_contexto_loja_falha(self):
        """Testa obter_contexto_loja quando winrt falha."""
        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"winrt.windows.services.store": None}):
                with self.assertRaises(OSError):
                    obter_contexto_loja()

    @patch("editor.core.servico_loja.obter_pacote_atual")
    def test_possui_identidade_pacote_quando_presente(self, mock_obter_pacote):
        """Deve retornar True quando o pacote MSIX possui identidade."""
        mock_pacote = MagicMock()
        mock_pacote.id.name = "ArestaClimbApps.EditorArestaClimb"
        mock_obter_pacote.return_value = mock_pacote

        self.assertTrue(self.servico.possui_identidade_pacote())

    @patch("editor.core.servico_loja.obter_pacote_atual")
    def test_possui_identidade_pacote_quando_ausente(self, mock_obter_pacote):
        """Deve retornar False quando levantar OSError/WinError 15700 ou None (ambiente dev)."""
        mock_obter_pacote.side_effect = OSError(15700, "O processo não tem identidade de pacote.")

        self.assertFalse(self.servico.possui_identidade_pacote())

    @patch("editor.core.servico_loja.obter_pacote_atual")
    def test_possui_identidade_pacote_quando_modulo_winrt_ausente(self, mock_obter_pacote):
        """Deve retornar False quando winrt não estiver instalado ou falhar import."""
        mock_obter_pacote.side_effect = ImportError("No module named winrt")

        self.assertFalse(self.servico.possui_identidade_pacote())

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=False)
    def test_verificar_atualizacoes_fora_da_store_retorna_nao_aplicavel(self, mock_possui_id):
        """Se o app rodar fora da Store (ex: Python dev ou CI), deve retornar status NAO_APLICAVEL imediatamente."""
        resultado = self.servico.verificar_atualizacoes_disponiveis()

        self.assertEqual(resultado.status, StatusAtualizacao.NAO_APLICAVEL)
        self.assertFalse(resultado.tem_atualizacao)
        self.assertFalse(resultado.obrigatoria)

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_sem_updates_disponiveis(self, mock_obter_contexto, mock_possui_id):
        """Quando a Store não tiver atualizações, deve retornar SEM_ATUALIZACAO."""
        mock_contexto = MagicMock()
        mock_contexto.get_app_and_optional_store_package_updates.return_value = []
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()

        self.assertEqual(resultado.status, StatusAtualizacao.SEM_ATUALIZACAO)
        self.assertFalse(resultado.tem_atualizacao)

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_com_update_opcional(self, mock_obter_contexto, mock_possui_id):
        """Quando a Store tiver atualizações não obrigatórias, deve retornar ATUALIZACAO_DISPONIVEL."""
        mock_update = MagicMock()
        mock_update.is_mandatory = False
        mock_update.package.id.version.major = 1
        mock_update.package.id.version.minor = 2
        mock_update.package.id.version.build = 0
        mock_update.package.id.version.revision = 0

        mock_contexto = MagicMock()
        mock_contexto.get_app_and_optional_store_package_updates.return_value = [mock_update]
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()

        self.assertEqual(resultado.status, StatusAtualizacao.ATUALIZACAO_DISPONIVEL)
        self.assertTrue(resultado.tem_atualizacao)
        self.assertFalse(resultado.obrigatoria)
        self.assertEqual(resultado.versao_disponivel, "1.2.0.0")

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_com_metodo_async(self, mock_obter_contexto, mock_possui_id):
        """Testa quando o contexto fornece apenas get_app_and_optional_store_package_updates_async."""
        mock_update = MagicMock()
        mock_update.is_mandatory = False
        mock_update.package.id.version.major = 1
        mock_update.package.id.version.minor = 0
        mock_update.package.id.version.build = 0
        mock_update.package.id.version.revision = 0

        mock_contexto = MagicMock(spec=["get_app_and_optional_store_package_updates_async"])
        mock_contexto.get_app_and_optional_store_package_updates_async.return_value = [mock_update]
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()
        self.assertEqual(resultado.status, StatusAtualizacao.ATUALIZACAO_DISPONIVEL)

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_sem_metodos_validos_no_contexto(self, mock_obter_contexto, mock_possui_id):
        """Testa quando o contexto não expõe nenhum método reconhecido."""
        mock_contexto = MagicMock(spec=[])
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()
        self.assertEqual(resultado.status, StatusAtualizacao.SEM_ATUALIZACAO)

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_quando_versao_falha(self, mock_obter_contexto, mock_possui_id):
        """Testa quando a extração da string de versão do pacote falha."""
        mock_update = MagicMock()
        mock_update.is_mandatory = False
        del mock_update.package.id.version # Força falha ao acessar versao

        mock_contexto = MagicMock()
        mock_contexto.get_app_and_optional_store_package_updates.return_value = [mock_update]
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()
        self.assertEqual(resultado.status, StatusAtualizacao.ATUALIZACAO_DISPONIVEL)
        self.assertIsNone(resultado.versao_disponivel)

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_com_update_obrigatorio(self, mock_obter_contexto, mock_possui_id):
        """Quando a Store indicar que o pacote é mandatory, deve retornar ATUALIZACAO_OBRIGATORIA."""
        mock_update = MagicMock()
        mock_update.is_mandatory = True
        mock_update.package.id.version.major = 2
        mock_update.package.id.version.minor = 0
        mock_update.package.id.version.build = 0
        mock_update.package.id.version.revision = 0

        mock_contexto = MagicMock()
        mock_contexto.get_app_and_optional_store_package_updates.return_value = [mock_update]
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()

        self.assertEqual(resultado.status, StatusAtualizacao.ATUALIZACAO_OBRIGATORIA)
        self.assertTrue(resultado.tem_atualizacao)
        self.assertTrue(resultado.obrigatoria)
        self.assertEqual(resultado.versao_disponivel, "2.0.0.0")

    @patch.object(ServicoLoja, "possui_identidade_pacote", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_verificar_atualizacoes_falha_de_rede_retorna_erro_com_fallback(self, mock_obter_contexto, mock_possui_id):
        """Em caso de falha de conexão na API da Store, deve retornar ERRO_CHECAGEM sem crashar."""
        mock_contexto = MagicMock()
        mock_contexto.get_app_and_optional_store_package_updates.side_effect = Exception("Store connection timeout")
        mock_obter_contexto.return_value = mock_contexto

        resultado = self.servico.verificar_atualizacoes_disponiveis()

        self.assertEqual(resultado.status, StatusAtualizacao.ERRO_CHECAGEM)
        self.assertFalse(resultado.tem_atualizacao)
        self.assertIn("Store connection timeout", resultado.mensagem)

    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_solicitar_instalacao_in_app_sucesso(self, mock_obter_contexto):
        """Deve chamar request_download_and_install_store_package_updates com sucesso."""
        mock_contexto = MagicMock()
        mock_contexto.request_download_and_install_store_package_updates.return_value = MagicMock()
        mock_obter_contexto.return_value = mock_contexto

        resultado = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            pacotes_atualizacao=[MagicMock()]
        )

        sucesso = self.servico.solicitar_instalacao_atualizacao(resultado)
        self.assertTrue(sucesso)
        mock_contexto.request_download_and_install_store_package_updates.assert_called_once()

    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_solicitar_instalacao_in_app_com_metodo_async(self, mock_obter_contexto):
        """Deve chamar request_download_and_install_store_package_updates_async com sucesso."""
        mock_contexto = MagicMock(spec=["request_download_and_install_store_package_updates_async"])
        mock_contexto.request_download_and_install_store_package_updates_async.return_value = MagicMock()
        mock_obter_contexto.return_value = mock_contexto

        resultado = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            pacotes_atualizacao=[MagicMock()]
        )

        sucesso = self.servico.solicitar_instalacao_atualizacao(resultado)
        self.assertTrue(sucesso)
        mock_contexto.request_download_and_install_store_package_updates_async.assert_called_once()

    @patch.object(ServicoLoja, "verificar_atualizacoes_disponiveis")
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_solicitar_instalacao_sem_resultado_busca_pacotes(self, mock_obter_contexto, mock_verificar):
        """Quando chamado sem resultado, busca os pacotes e executa."""
        mock_verificar.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            pacotes_atualizacao=[MagicMock()]
        )
        mock_contexto = MagicMock()
        mock_obter_contexto.return_value = mock_contexto

        sucesso = self.servico.solicitar_instalacao_atualizacao(None)
        self.assertTrue(sucesso)
        mock_verificar.assert_called_once()

    @patch.object(ServicoLoja, "verificar_atualizacoes_disponiveis")
    @patch.object(ServicoLoja, "abrir_pagina_na_loja", return_value=True)
    def test_solicitar_instalacao_sem_pacotes_faz_fallback_direto(self, mock_abrir_loja, mock_verificar):
        """Quando não há pacotes nem no resultado nem na busca, recorre ao fallback."""
        mock_verificar.return_value = ResultadoAtualizacao(
            status=StatusAtualizacao.SEM_ATUALIZACAO,
            pacotes_atualizacao=[]
        )

        sucesso = self.servico.solicitar_instalacao_atualizacao(None)
        self.assertTrue(sucesso)
        mock_abrir_loja.assert_called_once()

    @patch.object(ServicoLoja, "abrir_pagina_na_loja", return_value=True)
    @patch("editor.core.servico_loja.obter_contexto_loja")
    def test_solicitar_instalacao_in_app_falha_faz_fallback_para_deep_link(self, mock_obter_contexto, mock_abrir_loja):
        """Se a chamada in-app falhar, deve fazer fallback abrindo o protocolo ms-windows-store://."""
        mock_contexto = MagicMock()
        mock_contexto.request_download_and_install_store_package_updates.side_effect = Exception("HWND error")
        mock_obter_contexto.return_value = mock_contexto

        resultado = ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL,
            pacotes_atualizacao=[MagicMock()]
        )

        sucesso = self.servico.solicitar_instalacao_atualizacao(resultado)
        self.assertTrue(sucesso)
        mock_abrir_loja.assert_called_once()

    @patch("editor.core.servico_loja.QApplication.quit")
    @patch("editor.core.servico_loja.QDesktopServices.openUrl")
    def test_abrir_pagina_na_loja_abre_url_e_encerra_app(self, mock_open_url, mock_quit):
        """Deve abrir a URL ms-windows-store:// e solicitar o fechamento do app para atualização limpa."""
        sucesso = self.servico.abrir_pagina_na_loja("fake_id")

        self.assertTrue(sucesso)
        mock_open_url.assert_called_once()
        args, _ = mock_open_url.call_args
        self.assertIn("ms-windows-store://pdp/?ProductId=fake_id", args[0].toString())
        mock_quit.assert_called_once()

    @patch("editor.core.servico_loja.QApplication.quit")
    @patch("editor.core.servico_loja.QDesktopServices.openUrl")
    def test_abrir_pagina_na_loja_sem_parametro_usa_id_padrao(self, mock_open_url, mock_quit):
        """Deve abrir a URL com o ID oficial do produto quando nenhum for informado."""
        servico = ServicoLoja()
        sucesso = servico.abrir_pagina_na_loja()
        self.assertTrue(sucesso)
        args, _ = mock_open_url.call_args
        self.assertIn("ms-windows-store://pdp/?ProductId=9N6CQNH78WN8", args[0].toString())
        mock_quit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
