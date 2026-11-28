# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Testes orientados a comportamento e de integração para `editor.plataforma.windows.integracao`,
utilizando Fakes determinísticos (`api_win32_fake`) e validação real no Windows sem mocks.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from editor.core.configuracao_canal import obter_configuracao_canal
from editor.plataforma.contrato import ResultadoAtualizacao, StatusAtualizacao
from editor.plataforma.windows.api_win32_fake import (
    ApiWin32Fake,
    ProvedorKeyringWindowsFake,
    ServicoLojaWindowsFake,
)
from editor.plataforma.windows.integracao import (
    ESTILO_ESTENDIDO_APPWINDOW,
    ESTILO_MENU_SISTEMA,
    INDICE_ESTILO_ESTENDIDO,
    INDICE_ESTILO_PADRAO,
    AdaptadorWindows,
    _ApiWin32Sistema,
    _esta_executando_em_pacote_msix,
    _ProvedorKeyringWindowsSistema,
    aplicar_icone_janela_nativa,
    configurar_identidade_processo_windows,
    configurar_presenca_barra_de_tarefas,
    trazer_janela_para_frente,
)


def test_presenca_barra_de_tarefas_estilos_moldura_icone_e_nao_windows(tmp_path: Path) -> None:
    icone = tmp_path / "logo.ico"
    icone.write_bytes(b"ico")

    fake_linux = ApiWin32Fake(eh_windows=False)
    assert configurar_presenca_barra_de_tarefas(123, caminho_icone=icone, api_win32=fake_linux)

    fake_win = ApiWin32Fake(
        eh_windows=True,
        estilos_janela={
            (999, INDICE_ESTILO_ESTENDIDO): 0x00080000,
            (999, INDICE_ESTILO_PADRAO): 0x10000000,
        },
    )
    assert configurar_presenca_barra_de_tarefas(999, caminho_icone=icone, api_win32=fake_win)
    assert fake_win.estilos_janela[(999, INDICE_ESTILO_ESTENDIDO)] == (
        0x00080000 | ESTILO_ESTENDIDO_APPWINDOW
    )
    assert fake_win.estilos_janela[(999, INDICE_ESTILO_PADRAO)] == (
        0x10000000 | ESTILO_MENU_SISTEMA
    )
    assert fake_win.molduras_atualizadas == [999]
    assert fake_win.icones_hwnd[999] == str(icone.resolve())

    fake_erro = ApiWin32Fake(eh_windows=True, falhar_operacao=True)
    assert configurar_presenca_barra_de_tarefas(999, api_win32=fake_erro) is False
    assert aplicar_icone_janela_nativa(999, api_win32=fake_linux) is True
    assert aplicar_icone_janela_nativa(999, api_win32=fake_erro) is False


def test_configurar_identidade_processo_windows_aumid_e_registro(tmp_path: Path) -> None:
    icone = tmp_path / "logo.ico"
    icone.write_bytes(b"ico")

    # Fora do Windows: no-op retornando True
    assert configurar_identidade_processo_windows(
        "aresta.editor.v1", api_win32=ApiWin32Fake(eh_windows=False)
    )

    # Em pacote MSIX: preserva identidade nativa sem sobrescrever AUMID
    fake_msix = ApiWin32Fake(eh_windows=True, em_msix=True)
    assert configurar_identidade_processo_windows("aresta.editor.v1", api_win32=fake_msix)
    assert fake_msix.aumid_processo is None
    assert fake_msix.registro_aumid == {}

    # Python/Standalone: registra DisplayName + IconUri e define AUMID explícito
    fake_py = ApiWin32Fake(eh_windows=True, em_msix=False)
    assert configurar_identidade_processo_windows(
        "aresta.editor.v1",
        nome_exibicao="",
        caminho_icone=icone,
        api_win32=fake_py,
    )
    assert fake_py.aumid_processo == "aresta.editor.v1"
    assert fake_py.registro_aumid["aresta.editor.v1"]["DisplayName"] == "Editor Aresta"
    assert fake_py.registro_aumid["aresta.editor.v1"]["IconUri"] == str(icone.resolve())

    # Falha na fronteira retorna False com resiliência
    assert (
        configurar_identidade_processo_windows(
            "aresta.editor.v1", api_win32=ApiWin32Fake(falhar_operacao=True)
        )
        is False
    )


def test_msix_e_trazer_janela_para_frente_com_fakes() -> None:
    assert _esta_executando_em_pacote_msix(ApiWin32Fake(eh_windows=False)) is False
    assert _esta_executando_em_pacote_msix(ApiWin32Fake(eh_windows=True, em_msix=True)) is True
    assert _esta_executando_em_pacote_msix(ApiWin32Fake(falhar_operacao=True)) is False

    assert trazer_janela_para_frente(50, api_win32=ApiWin32Fake(eh_windows=False)) is True
    fake_ok = ApiWin32Fake(eh_windows=True)
    assert trazer_janela_para_frente(50, api_win32=fake_ok) is True
    assert fake_ok.janelas_focadas == [50]
    assert trazer_janela_para_frente(50, api_win32=ApiWin32Fake(falhar_operacao=True)) is False


def test_adaptador_windows_fachada_completa(tmp_path: Path) -> None:
    loja = ServicoLojaWindowsFake(
        resultado=ResultadoAtualizacao(
            status=StatusAtualizacao.ATUALIZACAO_DISPONIVEL, versao_disponivel="2.0.0"
        )
    )
    api = ApiWin32Fake(eh_windows=True, em_msix=False)
    cofre = ProvedorKeyringWindowsFake(backend_inicial_operacional=False)
    adaptador = AdaptadorWindows(servico_loja=loja, api_win32=api, provedor_keyring=cofre)

    qt_qpa_antigo = os.environ.pop("QT_QPA_PLATFORM", None)
    try:
        adaptador.configurar_ambiente_plataforma()
        assert os.environ.get("QT_QPA_PLATFORM") == "windows:darkmode=0"
    finally:
        os.environ.pop("QT_QPA_PLATFORM", None)
        if qt_qpa_antigo is not None:
            os.environ["QT_QPA_PLATFORM"] = qt_qpa_antigo

    adaptador_linux = AdaptadorWindows(
        servico_loja=loja, api_win32=ApiWin32Fake(eh_windows=False), provedor_keyring=cofre
    )
    adaptador_linux.configurar_ambiente_plataforma()

    icone_padrao = obter_configuracao_canal().obter_caminho_icone_aplicacao()
    assert adaptador.configurar_identidade_processo("aresta.editor.v1", nome_exibicao="Aresta")
    assert api.registro_aumid["aresta.editor.v1"]["IconUri"] == str(icone_padrao.resolve())
    assert adaptador.configurar_presenca_barra_de_tarefas(77) is True
    assert adaptador.aplicar_icone_janela_nativa(77) is True
    assert adaptador.trazer_janela_para_frente(77) is True
    assert adaptador.obter_nome_icone_preferencial() == "logo.ico"

    # Diretório de dados: Qt válido, fallback APPDATA e fallback Path.home()
    assert isinstance(adaptador.obter_diretorio_dados_usuario(), Path)
    assert (
        adaptador.obter_diretorio_dados_usuario(
            provedor_appdata_qt=lambda: "",
            ambiente={"APPDATA": str(tmp_path)},
        )
        == tmp_path / "EditorAresta"
    )
    dir_home = adaptador.obter_diretorio_dados_usuario(
        provedor_appdata_qt=lambda: "",
        ambiente={},
    )
    assert dir_home.name == "EditorAresta"

    # Loja
    res = adaptador.verificar_atualizacoes_disponiveis()
    assert res.versao_disponivel == "2.0.0"
    assert adaptador.solicitar_instalacao_atualizacao(res) is True
    assert loja.instalacoes == [res]

    # Cofre: instala quando inicialmente inoperante, preserva quando já operacional, e trata falhas
    assert adaptador.configurar_cofre_credenciais() is True
    assert cofre.backends_instalados == ["WinVaultKeyring"]
    assert adaptador.configurar_cofre_credenciais() is True
    assert len(cofre.backends_instalados) == 1

    adaptador_falha_consulta = AdaptadorWindows(
        servico_loja=loja,
        api_win32=api,
        provedor_keyring=ProvedorKeyringWindowsFake(falhar_consulta=True),
    )
    assert adaptador_falha_consulta.configurar_cofre_credenciais() is False

    adaptador_falha_inst = AdaptadorWindows(
        servico_loja=loja,
        api_win32=api,
        provedor_keyring=ProvedorKeyringWindowsFake(
            backend_inicial_operacional=False, falhar_instalacao=True
        ),
    )
    assert adaptador_falha_inst.configurar_cofre_credenciais() is False

    # Caminhos estendidos
    assert adaptador.normalizar_caminho_estendido("") == ""
    assert (
        adaptador.normalizar_caminho_estendido("\\\\?\\C:\\pasta\\arq.txt")
        == "\\\\?\\C:\\pasta\\arq.txt"
    )
    assert (
        adaptador.normalizar_caminho_estendido("\\\\servidor\\comp\\arq.txt")
        == "\\\\?\\UNC\\servidor\\comp\\arq.txt"
    )
    assert adaptador.normalizar_caminho_estendido(tmp_path / "croqui.yaml").startswith("\\\\?\\")


def test_integracao_real_subsistema_win32_e_keyring(qtbot, tmp_path: Path) -> None:
    """Exercita a implementação real `_ApiWin32Sistema` e `_ProvedorKeyringWindowsSistema` no Windows."""
    if sys.platform != "win32":
        return

    import winreg

    from PySide6.QtWidgets import QWidget

    prefixo_teste = r"Software\Classes\AppUserModelId\_ArestaTesteUnitario"
    api_real = _ApiWin32Sistema(prefixo_registro_aumid=prefixo_teste)
    assert api_real.plataforma_eh_windows() is True
    assert isinstance(api_real.esta_em_pacote_msix(), bool)

    try:
        assert api_real.registrar_metadados_aumid_usuario(
            "app.teste", "Aresta Teste", "C:\\logo.ico"
        )
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{prefixo_teste}\\app.teste") as chave_lida:
            assert winreg.QueryValueEx(chave_lida, "DisplayName")[0] == "Aresta Teste"
            assert winreg.QueryValueEx(chave_lida, "IconUri")[0] == "C:\\logo.ico"
    finally:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{prefixo_teste}\\app.teste")
        except OSError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, prefixo_teste)
        except OSError:
            pass

    assert api_real.definir_app_user_model_id("aresta.editor.v1") is True

    janela = QWidget()
    qtbot.addWidget(janela)
    hwnd = int(janela.winId())

    estilo_orig = api_real.obter_estilo_janela(hwnd, INDICE_ESTILO_ESTENDIDO)
    api_real.definir_estilo_janela(
        hwnd, INDICE_ESTILO_ESTENDIDO, estilo_orig | ESTILO_ESTENDIDO_APPWINDOW
    )
    api_real.atualizar_moldura_janela(hwnd)
    api_real.restaurar_e_focar_janela(hwnd)

    icone_real = str(obter_configuracao_canal().obter_caminho_icone_aplicacao())
    assert api_real.aplicar_icone_hwnd(hwnd, icone_real) is True
    assert api_real.aplicar_icone_hwnd(hwnd, "") is False

    ico_invalido = tmp_path / "corrompido.ico"
    ico_invalido.write_bytes(b"nao-eh-ico")
    assert api_real.aplicar_icone_hwnd(hwnd, str(ico_invalido)) is False

    provedor_kr = _ProvedorKeyringWindowsSistema()
    import keyring
    from keyring.backends import fail

    kr_anterior = keyring.get_keyring()
    try:
        keyring.set_keyring(fail.Keyring())
        assert provedor_kr.backend_atual_eh_operacional() is False
        provedor_kr.instalar_win_vault_keyring()
        assert provedor_kr.backend_atual_eh_operacional() is True
    finally:
        keyring.set_keyring(kr_anterior)
