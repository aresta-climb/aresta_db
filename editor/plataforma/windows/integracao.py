# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o subsistema Win32 e Shell do Windows.
Implementa o AdaptadorWindows conforme o protocolo AdaptadorPlataforma.
"""

import sys
import os
from pathlib import Path
from typing import Any, Optional
from PySide6.QtCore import QStandardPaths
from editor.plataforma.contrato import AdaptadorPlataforma, ResultadoAtualizacao
from editor.plataforma.windows.servico_loja import ServicoLoja

# Constantes da API Win32 para manipulação de estilos de janela
INDICE_ESTILO_ESTENDIDO: int = -20  # GWL_EXSTYLE
INDICE_ESTILO_PADRAO: int = -16  # GWL_STYLE

ESTILO_ESTENDIDO_APPWINDOW: int = 0x00040000  # WS_EX_APPWINDOW
ESTILO_MENU_SISTEMA: int = 0x00080000  # WS_SYSMENU


def _obter_user32() -> Any:
    """Retorna a biblioteca user32 do Win32 configurada com os tipos de chamada."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    return user32


def configurar_presenca_barra_de_tarefas(identificador_janela: int) -> bool:
    """
    Configura os estilos estendidos de janela no Windows para assegurar que janelas
    sem moldura (frameless) sejam exibidas com ícone na barra de tarefas e no alternador
    de janelas (Alt+Tab).
    """
    if sys.platform != "win32":
        return True

    try:
        user32 = _obter_user32()

        estilo_estendido_atual: int = int(
            user32.GetWindowLongW(identificador_janela, INDICE_ESTILO_ESTENDIDO)
        )
        estilo_padrao_atual: int = int(
            user32.GetWindowLongW(identificador_janela, INDICE_ESTILO_PADRAO)
        )

        user32.SetWindowLongW(
            identificador_janela,
            INDICE_ESTILO_ESTENDIDO,
            estilo_estendido_atual | ESTILO_ESTENDIDO_APPWINDOW,
        )

        user32.SetWindowLongW(
            identificador_janela,
            INDICE_ESTILO_PADRAO,
            estilo_padrao_atual | ESTILO_MENU_SISTEMA,
        )

        return True
    except Exception:
        return False


def _esta_executando_em_pacote_msix() -> bool:
    """
    Verifica se o processo atual está sendo executado dentro de um pacote MSIX com identidade própria.
    """
    if sys.platform != "win32":
        return False

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        comprimento = wintypes.UINT(0)
        resultado = kernel32.GetCurrentPackageFamilyName(ctypes.byref(comprimento), None)
        return bool(resultado == 0)
    except Exception:
        return False


def configurar_identidade_processo_windows(app_user_model_id: str) -> bool:
    """
    Configura explicitamente o AppUserModelID para processos standalone ou em desenvolvimento local.
    Caso a aplicação esteja rodando dentro de um pacote MSIX, a identidade nativa do pacote é
    preservada para assegurar a correspondência correta com os ícones e atalhos do Windows Shell.
    """
    if sys.platform != "win32":
        return True

    try:
        if _esta_executando_em_pacote_msix():
            return True

        import ctypes

        resultado_hresult = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            app_user_model_id
        )
        return bool(resultado_hresult == 0)
    except Exception:
        return False


def trazer_janela_para_frente(identificador_janela: int) -> bool:
    """
    Traz uma janela para o primeiro plano no Windows utilizando a API Win32.
    Restaura a janela caso esteja minimizada e define o foco de primeiro plano.
    """
    if sys.platform != "win32":
        return True

    try:
        user32 = _obter_user32()
        sw_restore: int = 9
        user32.ShowWindow(identificador_janela, sw_restore)
        user32.SetForegroundWindow(identificador_janela)
        return True
    except Exception:
        return False


class AdaptadorWindows(AdaptadorPlataforma):
    """Adaptador de integração nativa com o sistema operacional Windows."""

    def __init__(self, servico_loja: Optional[ServicoLoja] = None) -> None:
        self.servico_loja: ServicoLoja = servico_loja or ServicoLoja()

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        if sys.platform == "win32":
            os.environ.setdefault("QT_QPA_PLATFORM", "windows:darkmode=0")

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        """Aplica estilos estendidos WS_EX_APPWINDOW e WS_SYSMENU."""
        return configurar_presenca_barra_de_tarefas(identificador_janela)

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        """Configura o AppUserModelID explícito no Shell do Windows."""
        return configurar_identidade_processo_windows(identificador_app)

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        """Restaura e eleva a janela via Win32."""
        return trazer_janela_para_frente(identificador_janela)

    def obter_diretorio_dados_usuario(self) -> Path:
        """Retorna o diretório canônico %APPDATA%/EditorAresta."""
        appdata = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not appdata:
            appdata_env = os.environ.get("APPDATA")
            if appdata_env:
                return Path(appdata_env) / "EditorAresta"
            return Path.home() / "AppData" / "Roaming" / "EditorAresta"
        return Path(appdata)

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """Consulta a Microsoft Store por atualizações."""
        return self.servico_loja.verificar_atualizacoes_disponiveis()

    def solicitar_instalacao_atualizacao(
        self, resultado: Optional[ResultadoAtualizacao] = None
    ) -> bool:
        """Dispara a instalação in-app via WinRT ou fallback na loja."""
        return self.servico_loja.solicitar_instalacao_atualizacao(resultado)

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o Windows (.ico)."""
        return "logo.ico"

    def configurar_cofre_credenciais(self) -> None:
        """Garante a seleção do WinVaultKeyring no Windows para contornar limitações do PyInstaller."""
        try:
            import keyring
            from keyring.backends import fail

            backend_atual = keyring.get_keyring()
            if not isinstance(backend_atual, fail.Keyring):
                return
        except Exception:
            return

        try:
            from keyring.backends import Windows

            keyring.set_keyring(Windows.WinVaultKeyring())  # type: ignore[no-untyped-call]
        except Exception:
            pass

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """
        No Windows, prefixa caminhos absolutos com \\?\\ para contornar o limite MAX_PATH de 260 caracteres.
        Preserva caminhos já normalizados e suporta caminhos de rede UNC.
        """
        if not caminho:
            return ""
        caminho_str = str(caminho)
        if caminho_str.startswith("\\\\?\\"):
            return caminho_str

        caminho_abs = str(Path(caminho).resolve())
        if caminho_abs.startswith("\\\\"):
            return f"\\\\?\\UNC\\{caminho_abs[2:]}"
        return f"\\\\?\\{caminho_abs}"
