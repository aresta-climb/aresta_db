# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o subsistema Win32 e Shell do Windows.
Implementa o AdaptadorWindows conforme o protocolo AdaptadorPlataforma.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QStandardPaths

from editor.plataforma.contrato import AdaptadorPlataforma, ResultadoAtualizacao
from editor.plataforma.windows.servico_loja import ServicoLoja

# Constantes da API Win32 para manipulação de estilos e moldura de janela
INDICE_ESTILO_ESTENDIDO: int = -20  # GWL_EXSTYLE
INDICE_ESTILO_PADRAO: int = -16  # GWL_STYLE

ESTILO_ESTENDIDO_APPWINDOW: int = 0x00040000  # WS_EX_APPWINDOW
ESTILO_MENU_SISTEMA: int = 0x00080000  # WS_SYSMENU
SWP_ATUALIZAR_MOLDURA: int = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020


class ProvedorApiWin32(Protocol):
    """Contrato para isolamento determinístico de chamadas nativas Win32 e Registro."""

    def plataforma_eh_windows(self) -> bool: ...
    def esta_em_pacote_msix(self) -> bool: ...
    def definir_app_user_model_id(self, app_id: str) -> bool: ...
    def registrar_metadados_aumid_usuario(
        self,
        app_id: str,
        nome_exibicao: str,
        caminho_icone: str,
    ) -> bool: ...
    def obter_estilo_janela(self, identificador_janela: int, indice: int) -> int: ...
    def definir_estilo_janela(
        self, identificador_janela: int, indice: int, novo_estilo: int
    ) -> None: ...
    def atualizar_moldura_janela(self, identificador_janela: int) -> None: ...
    def aplicar_icone_hwnd(self, identificador_janela: int, caminho_icone: str) -> bool: ...
    def restaurar_e_focar_janela(self, identificador_janela: int) -> None: ...


class ProvedorKeyringWindows(Protocol):
    """Contrato para consulta e instalação do backend WinVaultKeyring."""

    def backend_atual_eh_operacional(self) -> bool: ...
    def instalar_win_vault_keyring(self) -> Any: ...


def _obter_user32() -> Any:
    """Retorna a biblioteca user32 do Win32 configurada com os tipos de chamada."""
    import ctypes
    from ctypes import wintypes

    windll: Any = getattr(ctypes, "windll")
    user32 = windll.user32
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.SendMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.SendMessageW.restype = wintypes.LPARAM
    return user32


class _ApiWin32Sistema:
    """Implementação real das operações Win32 sobre `ctypes.windll` e `winreg`."""

    def __init__(self, prefixo_registro_aumid: str = r"Software\Classes\AppUserModelId") -> None:
        self.prefixo_registro_aumid = prefixo_registro_aumid

    def plataforma_eh_windows(self) -> bool:
        return sys.platform == "win32"

    def esta_em_pacote_msix(self) -> bool:
        import ctypes
        from ctypes import wintypes

        windll: Any = getattr(ctypes, "windll")
        kernel32 = windll.kernel32
        comprimento = wintypes.UINT(0)
        resultado = kernel32.GetCurrentPackageFamilyName(ctypes.byref(comprimento), None)
        return bool(resultado == 0)

    def definir_app_user_model_id(self, app_id: str) -> bool:
        import ctypes

        windll: Any = getattr(ctypes, "windll")
        shell32 = windll.shell32
        shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        resultado_hresult = shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return bool(resultado_hresult == 0)

    def registrar_metadados_aumid_usuario(
        self,
        app_id: str,
        nome_exibicao: str,
        caminho_icone: str,
    ) -> bool:
        import importlib

        winreg_mod: Any = importlib.import_module("winreg")
        caminho_chave = f"{self.prefixo_registro_aumid}\\{app_id}"
        with winreg_mod.CreateKeyEx(
            winreg_mod.HKEY_CURRENT_USER,
            caminho_chave,
            0,
            winreg_mod.KEY_WRITE,
        ) as chave:
            if nome_exibicao:
                winreg_mod.SetValueEx(chave, "DisplayName", 0, winreg_mod.REG_SZ, nome_exibicao)
            if caminho_icone:
                winreg_mod.SetValueEx(chave, "IconUri", 0, winreg_mod.REG_SZ, caminho_icone)
        return True

    def obter_estilo_janela(self, identificador_janela: int, indice: int) -> int:
        return int(_obter_user32().GetWindowLongW(identificador_janela, indice))

    def definir_estilo_janela(
        self, identificador_janela: int, indice: int, novo_estilo: int
    ) -> None:
        _obter_user32().SetWindowLongW(identificador_janela, indice, novo_estilo)

    def atualizar_moldura_janela(self, identificador_janela: int) -> None:
        _obter_user32().SetWindowPos(identificador_janela, 0, 0, 0, 0, 0, SWP_ATUALIZAR_MOLDURA)

    def aplicar_icone_hwnd(self, identificador_janela: int, caminho_icone: str) -> bool:
        if not caminho_icone or not Path(caminho_icone).is_file():
            return False
        user32 = _obter_user32()
        flags_icone = 0x00000010 | 0x00008000  # LR_LOADFROMFILE | LR_SHARED
        hicon_pequeno = int(user32.LoadImageW(None, caminho_icone, 1, 16, 16, flags_icone) or 0)
        hicon_grande = int(user32.LoadImageW(None, caminho_icone, 1, 32, 32, flags_icone) or 0)
        if not hicon_pequeno and not hicon_grande:
            return False
        wm_seticon = 0x0080
        user32.SendMessageW(identificador_janela, wm_seticon, 0, hicon_pequeno)
        user32.SendMessageW(identificador_janela, wm_seticon, 1, hicon_grande)
        return True

    def restaurar_e_focar_janela(self, identificador_janela: int) -> None:
        user32 = _obter_user32()
        user32.ShowWindow(identificador_janela, 9)
        user32.SetForegroundWindow(identificador_janela)


class _ProvedorKeyringWindowsSistema:
    """Implementação real do provedor de cofre Windows usando `keyring`."""

    def backend_atual_eh_operacional(self) -> bool:
        import keyring
        from keyring.backends import fail

        return not isinstance(keyring.get_keyring(), fail.Keyring)

    def instalar_win_vault_keyring(self) -> Any:
        import keyring
        from keyring.backends import Windows

        instancia = Windows.WinVaultKeyring()  # type: ignore[no-untyped-call]
        keyring.set_keyring(instancia)
        return instancia


def _resolver_caminho_icone_padrao_windows() -> str:
    """Obtém o caminho absoluto do ícone `.ico` do canal atual quando disponível."""
    from editor.core.configuracao_canal import obter_configuracao_canal

    caminho = obter_configuracao_canal().obter_caminho_icone_aplicacao()
    return str(caminho.resolve()) if caminho.is_file() else ""


def _esta_executando_em_pacote_msix(api_win32: ProvedorApiWin32 | None = None) -> bool:
    """Verifica se o processo atual está sendo executado dentro de um pacote MSIX com identidade própria."""
    api = api_win32 or _ApiWin32Sistema()
    if not api.plataforma_eh_windows():
        return False
    try:
        return api.esta_em_pacote_msix()
    except Exception:
        return False


def aplicar_icone_janela_nativa(
    identificador_janela: int,
    caminho_icone: Path | str | None = None,
    api_win32: ProvedorApiWin32 | None = None,
) -> bool:
    """
    Aplica explicitamente os handles Win32 `WM_SETICON` (`ICON_SMALL` e `ICON_BIG`) no `HWND`,
    garantindo que barra de título e barra de tarefas exibam o ícone oficial mesmo via `python.exe`.
    """
    api = api_win32 or _ApiWin32Sistema()
    if not api.plataforma_eh_windows():
        return True
    try:
        caminho_str = (
            str(Path(caminho_icone).resolve())
            if caminho_icone
            else _resolver_caminho_icone_padrao_windows()
        )
        return api.aplicar_icone_hwnd(identificador_janela, caminho_str)
    except Exception:
        return False


def configurar_presenca_barra_de_tarefas(
    identificador_janela: int,
    caminho_icone: Path | str | None = None,
    api_win32: ProvedorApiWin32 | None = None,
) -> bool:
    """
    Configura os estilos estendidos `WS_EX_APPWINDOW` e `WS_SYSMENU`, notifica `SWP_FRAMECHANGED`
    e reforça o ícone nativo `WM_SETICON` para janelas sem moldura (frameless) no Windows.
    """
    api = api_win32 or _ApiWin32Sistema()
    if not api.plataforma_eh_windows():
        return True

    try:
        estilo_estendido_atual = api.obter_estilo_janela(
            identificador_janela, INDICE_ESTILO_ESTENDIDO
        )
        estilo_padrao_atual = api.obter_estilo_janela(identificador_janela, INDICE_ESTILO_PADRAO)

        api.definir_estilo_janela(
            identificador_janela,
            INDICE_ESTILO_ESTENDIDO,
            estilo_estendido_atual | ESTILO_ESTENDIDO_APPWINDOW,
        )
        api.definir_estilo_janela(
            identificador_janela,
            INDICE_ESTILO_PADRAO,
            estilo_padrao_atual | ESTILO_MENU_SISTEMA,
        )
        api.atualizar_moldura_janela(identificador_janela)
        aplicar_icone_janela_nativa(
            identificador_janela, caminho_icone=caminho_icone, api_win32=api
        )
        return True
    except Exception:
        return False


def configurar_identidade_processo_windows(
    app_user_model_id: str,
    nome_exibicao: str = "",
    caminho_icone: Path | str | None = None,
    api_win32: ProvedorApiWin32 | None = None,
) -> bool:
    """
    Configura explicitamente o `AppUserModelID` e registra `DisplayName` + `IconUri` em
    `HKCU\\Software\\Classes\\AppUserModelId\\<id>` para processos standalone ou Python local,
    preservando a identidade nativa quando executado dentro de pacote MSIX.
    """
    api = api_win32 or _ApiWin32Sistema()
    if not api.plataforma_eh_windows():
        return True

    try:
        if api.esta_em_pacote_msix():
            return True

        caminho_str = (
            str(Path(caminho_icone).resolve())
            if caminho_icone
            else _resolver_caminho_icone_padrao_windows()
        )
        nome_final = nome_exibicao.strip()
        if not nome_final:
            from editor.core.configuracao_canal import obter_configuracao_canal

            nome_final = obter_configuracao_canal().nome_aplicativo

        api.registrar_metadados_aumid_usuario(app_user_model_id, nome_final, caminho_str)
        return api.definir_app_user_model_id(app_user_model_id)
    except Exception:
        return False


def trazer_janela_para_frente(
    identificador_janela: int,
    api_win32: ProvedorApiWin32 | None = None,
) -> bool:
    """Restaura uma janela caso esteja minimizada e define o foco de primeiro plano no Windows."""
    api = api_win32 or _ApiWin32Sistema()
    if not api.plataforma_eh_windows():
        return True

    try:
        api.restaurar_e_focar_janela(identificador_janela)
        return True
    except Exception:
        return False


class AdaptadorWindows(AdaptadorPlataforma):
    """Adaptador de integração nativa com o sistema operacional Windows."""

    def __init__(
        self,
        servico_loja: Any | None = None,
        api_win32: ProvedorApiWin32 | None = None,
        provedor_keyring: ProvedorKeyringWindows | None = None,
    ) -> None:
        self.servico_loja: Any = servico_loja or ServicoLoja()
        self._api_win32: ProvedorApiWin32 = api_win32 or _ApiWin32Sistema()
        self._provedor_keyring: ProvedorKeyringWindows = (
            provedor_keyring or _ProvedorKeyringWindowsSistema()
        )

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        if self._api_win32.plataforma_eh_windows():
            os.environ.setdefault("QT_QPA_PLATFORM", "windows:darkmode=0")

    def configurar_presenca_barra_de_tarefas(
        self,
        identificador_janela: int,
        caminho_icone: Path | str | None = None,
    ) -> bool:
        """Aplica estilos estendidos `WS_EX_APPWINDOW`/`WS_SYSMENU`, moldura e ícone nativo."""
        return configurar_presenca_barra_de_tarefas(
            identificador_janela,
            caminho_icone=caminho_icone,
            api_win32=self._api_win32,
        )

    def configurar_identidade_processo(
        self,
        identificador_app: str,
        nome_exibicao: str = "",
        caminho_icone: Path | str | None = None,
    ) -> bool:
        """Configura o `AppUserModelID` explícito e metadados de ícone no Shell do Windows."""
        return configurar_identidade_processo_windows(
            identificador_app,
            nome_exibicao=nome_exibicao,
            caminho_icone=caminho_icone,
            api_win32=self._api_win32,
        )

    def aplicar_icone_janela_nativa(
        self,
        identificador_janela: int,
        caminho_icone: Path | str | None = None,
    ) -> bool:
        """Reforça o ícone nativo `WM_SETICON` no `HWND` informado."""
        return aplicar_icone_janela_nativa(
            identificador_janela,
            caminho_icone=caminho_icone,
            api_win32=self._api_win32,
        )

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        """Restaura e eleva a janela via Win32."""
        return trazer_janela_para_frente(identificador_janela, api_win32=self._api_win32)

    def obter_diretorio_dados_usuario(
        self,
        provedor_appdata_qt: Any | None = None,
        ambiente: dict[str, str] | None = None,
    ) -> Path:
        """Retorna o diretório canônico `%APPDATA%/EditorAresta`."""
        appdata = (
            provedor_appdata_qt()
            if callable(provedor_appdata_qt)
            else QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        )
        if not appdata:
            env_efetivo = ambiente if ambiente is not None else os.environ
            appdata_env = env_efetivo.get("APPDATA")
            if appdata_env:
                return Path(appdata_env) / "EditorAresta"
            return Path.home() / "AppData" / "Roaming" / "EditorAresta"
        return Path(appdata)

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """Consulta a Microsoft Store por atualizações."""
        res: ResultadoAtualizacao = self.servico_loja.verificar_atualizacoes_disponiveis()
        return res

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        """Dispara a instalação in-app via WinRT ou fallback na loja."""
        return bool(self.servico_loja.solicitar_instalacao_atualizacao(resultado))

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o Windows (.ico)."""
        return "logo.ico"

    def configurar_cofre_credenciais(self) -> bool:
        """Garante a seleção do WinVaultKeyring no Windows para contornar limitações do PyInstaller."""
        try:
            if self._provedor_keyring.backend_atual_eh_operacional():
                return True
        except Exception:
            return False

        try:
            self._provedor_keyring.instalar_win_vault_keyring()
            return True
        except Exception:
            return False

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """
        No Windows, prefixa caminhos absolutos com `\\\\?\\` para contornar o limite MAX_PATH de 260 caracteres.
        Preserva caminhos já normalizados e suporta caminhos de rede UNC.
        """
        if not caminho:
            return ""
        caminho_str = str(caminho)
        if caminho_str.startswith("\\\\?\\"):
            return caminho_str
        if caminho_str.startswith("\\\\"):
            return f"\\\\?\\UNC\\{caminho_str[2:]}"

        caminho_abs = str(Path(caminho).resolve())
        return f"\\\\?\\{caminho_abs}"
