# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes unitários para a ponte Sparkle Framework em editor.plataforma.macos.sparkle.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from editor.plataforma.macos.sparkle import (
    _obter_runtime_objc,
    carregar_biblioteca_sparkle,
    localizar_caminho_sparkle_framework,
    obter_controlador_sparkle,
    solicitar_verificacao_sparkle,
)


def test_obter_runtime_objc() -> None:
    """Valida o carregamento da biblioteca libobjc do sistema."""
    mock_lib = MagicMock()
    with patch("ctypes.cdll.LoadLibrary", return_value=mock_lib) as mock_load:
        res = _obter_runtime_objc()
        assert res == mock_lib
        mock_load.assert_called_once_with("/usr/lib/libobjc.A.dylib")


def test_localizar_caminho_sparkle_framework_em_bundle(tmp_path: Path) -> None:
    """Valida a resolução do Sparkle.framework dentro de Contents/Frameworks de um bundle .app."""
    app_dir = tmp_path / "EditorAresta.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    fw_dir = app_dir / "Contents" / "Frameworks" / "Sparkle.framework"
    macos_dir.mkdir(parents=True)
    fw_dir.mkdir(parents=True)

    executavel = macos_dir / "EditorAresta"
    executavel.write_bytes(b"binario")

    with patch("sys.executable", str(executavel)):
        caminho = localizar_caminho_sparkle_framework()
        assert caminho is not None
        assert caminho.resolve() == fw_dir.resolve()


def test_localizar_caminho_sparkle_framework_fallback_sistema(tmp_path: Path) -> None:
    """Valida a resolução do Sparkle.framework a partir de /Library/Frameworks."""
    executavel = tmp_path / "editor" / "main.py"
    executavel.parent.mkdir(parents=True)
    executavel.write_bytes(b"")

    caminho_sistema = Path("/Library/Frameworks/Sparkle.framework")

    def mock_exists(self: Path) -> bool:
        return self == caminho_sistema

    with patch("sys.executable", str(executavel)):
        with patch.object(Path, "exists", side_effect=mock_exists, autospec=True):
            caminho = localizar_caminho_sparkle_framework()
            assert caminho == caminho_sistema


def test_localizar_caminho_sparkle_framework_inexistente(tmp_path: Path) -> None:
    """Retorna None quando o Sparkle.framework não existe na árvore do bundle nem no sistema."""
    executavel = tmp_path / "editor" / "main.py"
    executavel.parent.mkdir(parents=True)
    executavel.write_bytes(b"")

    with patch("sys.executable", str(executavel)):
        with patch.object(Path, "exists", return_value=False):
            assert localizar_caminho_sparkle_framework() is None


def test_carregar_biblioteca_sparkle_nao_darwin() -> None:
    """Em sistemas diferentes de darwin (Linux/Windows), retorna None sem carregar bibliotecas C."""
    with patch("sys.platform", "linux"):
        assert carregar_biblioteca_sparkle() is None

    with patch("sys.platform", "win32"):
        assert carregar_biblioteca_sparkle() is None


def test_carregar_biblioteca_sparkle_darwin_sucesso(tmp_path: Path) -> None:
    """No darwin, carrega o framework via CDLL e retorna o handle."""
    caminho_fw = tmp_path / "Sparkle.framework"
    caminho_fw.mkdir()
    binario_fw = caminho_fw / "Sparkle"
    binario_fw.write_bytes(b"dylib")

    mock_cdll = MagicMock()
    with patch("sys.platform", "darwin"):
        with patch("ctypes.CDLL", return_value=mock_cdll) as mock_load:
            handle = carregar_biblioteca_sparkle(caminho_framework=caminho_fw)
            assert handle == mock_cdll
            mock_load.assert_called_once_with(str(binario_fw))


def test_carregar_biblioteca_sparkle_darwin_erro_oserror(tmp_path: Path) -> None:
    """Trata defensivamente erros de carregamento (OSError) retornando None."""
    caminho_fw = tmp_path / "Sparkle.framework"
    caminho_fw.mkdir()
    (caminho_fw / "Sparkle").write_bytes(b"dylib")

    with patch("sys.platform", "darwin"):
        with patch("ctypes.CDLL", side_effect=OSError("Biblioteca corrompida")):
            assert carregar_biblioteca_sparkle(caminho_framework=caminho_fw) is None


def test_carregar_biblioteca_sparkle_darwin_sem_caminho() -> None:
    """No darwin, se o caminho do framework não for localizado, retorna None."""
    with patch("sys.platform", "darwin"):
        with patch(
            "editor.plataforma.macos.sparkle.localizar_caminho_sparkle_framework", return_value=None
        ):
            assert carregar_biblioteca_sparkle(caminho_framework=None) is None


def test_obter_controlador_sparkle_sucesso() -> None:
    """Instancia ou obtém o SPUStandardUpdaterController via runtime Objective-C."""
    mock_lib_objc = MagicMock()
    mock_classe = MagicMock()
    mock_controlador = MagicMock()

    # Simula [SPUStandardUpdaterController sharedUpdaterController]
    mock_lib_objc.objc_getClass.return_value = 12345
    mock_lib_objc.sel_registerName.return_value = 67890
    mock_lib_objc.objc_msgSend.return_value = mock_controlador

    with patch(
        "editor.plataforma.macos.sparkle.carregar_biblioteca_sparkle", return_value=MagicMock()
    ):
        with patch(
            "editor.plataforma.macos.sparkle._obter_runtime_objc", return_value=mock_lib_objc
        ):
            controlador = obter_controlador_sparkle()
            assert controlador == mock_controlador


def test_obter_controlador_sparkle_sem_framework() -> None:
    """Retorna None quando o framework não pode ser carregado."""
    with patch("editor.plataforma.macos.sparkle.carregar_biblioteca_sparkle", return_value=None):
        assert obter_controlador_sparkle() is None


def test_obter_controlador_sparkle_classe_inexistente() -> None:
    """Retorna None quando a classe SPUStandardUpdaterController não for encontrada."""
    mock_lib_objc = MagicMock()
    mock_lib_objc.objc_getClass.return_value = None

    with patch(
        "editor.plataforma.macos.sparkle.carregar_biblioteca_sparkle", return_value=MagicMock()
    ):
        with patch(
            "editor.plataforma.macos.sparkle._obter_runtime_objc", return_value=mock_lib_objc
        ):
            assert obter_controlador_sparkle() is None


def test_obter_controlador_sparkle_erro_despacho() -> None:
    """Trata exceções durante a chamada Objective-C retornando None."""
    mock_lib_objc = MagicMock()
    mock_lib_objc.objc_getClass.return_value = 12345
    mock_lib_objc.objc_msgSend.side_effect = RuntimeError("Falha de runtime Cocoa")

    with patch(
        "editor.plataforma.macos.sparkle.carregar_biblioteca_sparkle", return_value=MagicMock()
    ):
        with patch(
            "editor.plataforma.macos.sparkle._obter_runtime_objc", return_value=mock_lib_objc
        ):
            assert obter_controlador_sparkle() is None


def test_solicitar_verificacao_sparkle_sucesso() -> None:
    """Chama checkForUpdates: com sucesso no controlador ativo."""
    mock_lib_objc = MagicMock()
    mock_controlador = 99999

    with patch("editor.plataforma.macos.sparkle._obter_runtime_objc", return_value=mock_lib_objc):
        resultado = solicitar_verificacao_sparkle(controlador=mock_controlador)
        assert resultado is True
        mock_lib_objc.objc_msgSend.assert_called_once()


def test_solicitar_verificacao_sparkle_sem_controlador() -> None:
    """Retorna False se o controlador informado for None e não puder ser obtido."""
    with patch("editor.plataforma.macos.sparkle.obter_controlador_sparkle", return_value=None):
        assert solicitar_verificacao_sparkle(controlador=None) is False


def test_solicitar_verificacao_sparkle_erro_despacho() -> None:
    """Trata exceção durante a chamada checkForUpdates: retornando False."""
    mock_lib_objc = MagicMock()
    mock_lib_objc.objc_msgSend.side_effect = RuntimeError("Erro de envio de mensagem")

    with patch("editor.plataforma.macos.sparkle._obter_runtime_objc", return_value=mock_lib_objc):
        assert solicitar_verificacao_sparkle(controlador=12345) is False
