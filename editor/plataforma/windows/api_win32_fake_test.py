# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""Testes unitários espelhados para a biblioteca test-only `api_win32_fake`."""

import pytest

from editor.plataforma.contrato import StatusAtualizacao
from editor.plataforma.windows.api_win32_fake import (
    ApiWin32Fake,
    ProvedorKeyringWindowsFake,
    ServicoLojaWindowsFake,
)


def test_api_win32_fake_fluxo_deterministico_em_memoria() -> None:
    fake = ApiWin32Fake(eh_windows=True, em_msix=False)
    assert fake.plataforma_eh_windows() is True
    assert fake.esta_em_pacote_msix() is False

    assert fake.definir_app_user_model_id("aresta.editor.v1") is True
    assert fake.aumid_processo == "aresta.editor.v1"

    assert (
        fake.registrar_metadados_aumid_usuario(
            "aresta.editor.v1", "Editor Aresta", "C:\\icone\\logo.ico"
        )
        is True
    )
    assert fake.registro_aumid["aresta.editor.v1"] == {
        "DisplayName": "Editor Aresta",
        "IconUri": "C:\\icone\\logo.ico",
    }

    assert fake.obter_estilo_janela(10, -20) == 0
    fake.definir_estilo_janela(10, -20, 0x00040000)
    assert fake.obter_estilo_janela(10, -20) == 0x00040000
    fake.atualizar_moldura_janela(10)
    assert fake.molduras_atualizadas == [10]

    assert fake.aplicar_icone_hwnd(10, "") is False
    assert fake.aplicar_icone_hwnd(10, "C:\\icone\\logo.ico") is True
    assert fake.icones_hwnd[10] == "C:\\icone\\logo.ico"

    fake.restaurar_e_focar_janela(10)
    assert fake.janelas_focadas == [10]


def test_api_win32_fake_hresult_erro_nao_windows_e_excecao() -> None:
    fake_linux = ApiWin32Fake(eh_windows=False, em_msix=True, hresult_aumid=-1)
    assert fake_linux.plataforma_eh_windows() is False
    assert fake_linux.esta_em_pacote_msix() is False
    assert fake_linux.definir_app_user_model_id("aresta.editor.v1") is False
    assert fake_linux.registrar_metadados_aumid_usuario("id", "", "") is True
    assert fake_linux.registro_aumid["id"] == {}

    fake_erro = ApiWin32Fake(falhar_operacao=True)
    with pytest.raises(OSError):
        fake_erro.esta_em_pacote_msix()


def test_provedor_keyring_windows_fake_comportamentos() -> None:
    fake = ProvedorKeyringWindowsFake(backend_inicial_operacional=False)
    assert fake.backend_atual_eh_operacional() is False
    assert fake.instalar_win_vault_keyring() == "WinVaultKeyring"
    assert fake.backend_atual_eh_operacional() is True
    assert fake.backends_instalados == ["WinVaultKeyring"]

    fake_falha_consulta = ProvedorKeyringWindowsFake(falhar_consulta=True)
    with pytest.raises(RuntimeError):
        fake_falha_consulta.backend_atual_eh_operacional()

    fake_falha_inst = ProvedorKeyringWindowsFake(
        backend_inicial_operacional=False, falhar_instalacao=True
    )
    with pytest.raises(RuntimeError):
        fake_falha_inst.instalar_win_vault_keyring()


def test_servico_loja_windows_fake_comportamento() -> None:
    loja = ServicoLojaWindowsFake()
    res = loja.verificar_atualizacoes_disponiveis()
    assert res.status == StatusAtualizacao.SEM_ATUALIZACAO
    assert loja.solicitar_instalacao_atualizacao(res) is True
    assert loja.instalacoes == [res]
