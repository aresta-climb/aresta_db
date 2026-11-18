# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import subprocess
from pathlib import Path

import pytest

from editor.executor_build_fake import ExecutorBuildFake, ExecutorBuildProtocolo


def test_executor_build_fake_cumpre_protocolo_e_resolve_executaveis() -> None:
    """Valida que ExecutorBuildFake implementa o protocolo e consulta o mapa de executáveis."""
    fake = ExecutorBuildFake(executaveis={"uv": "/bin/uv", "flatpak": None})
    assert isinstance(fake, ExecutorBuildProtocolo)
    assert fake.qual_executavel("uv") == "/bin/uv"
    assert fake.qual_executavel("flatpak") is None
    assert fake.qual_executavel("inexistente") is None


def test_executor_build_fake_enfileira_respostas_e_verifica_erro() -> None:
    """Valida fila determinística de respostas de comandos e exceção quando verificar=True."""
    fake = ExecutorBuildFake()
    fake.enfileirar_resposta_comando(returncode=0, stdout="ok\n")
    fake.enfileirar_resposta_comando(returncode=2, stderr="falha")

    res_ok = fake.executar_comando(["eco", "1"], capturar_saida=True)
    assert res_ok.returncode == 0
    assert res_ok.stdout == "ok\n"

    with pytest.raises(subprocess.CalledProcessError) as exc:
        fake.executar_comando(["eco", "2"], verificar=True)
    assert exc.value.returncode == 2

    res_padrao = fake.executar_comando(["eco", "3"])
    assert res_padrao.returncode == 0
    assert len(fake.comandos_executados) == 3


def test_executor_build_fake_suporta_manipulador_customizado(tmp_path: Path) -> None:
    """Valida execução com manipulador determinístico inspecionando cwd e argumentos."""

    def manipulador(
        cmd: list[str], cwd: Path | None, capturar: bool, verificar: bool
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert capturar is True
        assert verificar is False
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="gerado")

    fake = ExecutorBuildFake(manipulador_comando=manipulador)
    res = fake.executar_comando(["uv", "export"], cwd=tmp_path, capturar_saida=True)
    assert res.stdout == "gerado"


def test_executor_build_fake_simula_pyinstaller_e_pytest() -> None:
    """Valida registro de chamadas de PyInstaller/pytest e erro quando PyInstaller indisponível."""
    fake = ExecutorBuildFake(pyinstaller_disponivel=True, codigo_pytest=5)
    fake.executar_pyinstaller(["EditorAresta.spec", "--clean"])
    assert fake.chamadas_pyinstaller == [["EditorAresta.spec", "--clean"]]
    assert fake.executar_pytest(["editor", "-v"]) == 5
    assert fake.chamadas_pytest == [["editor", "-v"]]

    fake_sem_pyi = ExecutorBuildFake(pyinstaller_disponivel=False)
    with pytest.raises(RuntimeError, match="PyInstaller não está disponível"):
        fake_sem_pyi.executar_pyinstaller(["EditorAresta.spec"])
