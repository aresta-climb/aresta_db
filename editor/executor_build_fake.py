# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Fake determinístico em memória para a fronteira de processos externos de empacotamento
(PyInstaller, flatpak-builder, flatpak, uv, ruff e pytest) utilizada por editor/build.py.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExecutorBuildProtocolo(Protocol):
    """Contrato da fronteira de execução de ferramentas externas de build e teste."""

    def qual_executavel(self, nome: str) -> str | None:
        """Retorna o caminho de um executável no PATH ou None se ausente."""
        ...

    def executar_comando(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        capturar_saida: bool = False,
        verificar: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Executa um comando externo de sistema operacional."""
        ...

    def executar_pyinstaller(self, argumentos: list[str]) -> None:
        """Executa o empacotador PyInstaller com os argumentos informados."""
        ...

    def executar_pytest(self, argumentos: list[str]) -> int:
        """Executa a suíte do pytest com os argumentos informados e retorna o código de saída."""
        ...


class ExecutorBuildFake:
    """
    Implementação determinística em memória de ExecutorBuildProtocolo para testes de build,
    suportando configuração de executáveis presentes, respostas de subprocessos, falhas
    simuladas de PyInstaller ausente e captura integral de chamadas realizadas.
    """

    def __init__(
        self,
        *,
        executaveis: dict[str, str | None] | None = None,
        pyinstaller_disponivel: bool = True,
        codigo_pytest: int = 0,
        manipulador_comando: Callable[
            [list[str], Path | None, bool, bool], subprocess.CompletedProcess[str]
        ]
        | None = None,
    ) -> None:
        self.executaveis: dict[str, str | None] = (
            dict(executaveis)
            if executaveis is not None
            else {
                "uv": "/usr/bin/uv",
                "flatpak": "/usr/bin/flatpak",
                "flatpak-builder": "/usr/bin/flatpak-builder",
            }
        )
        self.pyinstaller_disponivel: bool = pyinstaller_disponivel
        self.codigo_pytest: int = codigo_pytest
        self.manipulador_comando = manipulador_comando
        self.fila_respostas_comandos: list[subprocess.CompletedProcess[str]] = []
        self.comandos_executados: list[list[str]] = []
        self.chamadas_pyinstaller: list[list[str]] = []
        self.chamadas_pytest: list[list[str]] = []

    def enfileirar_resposta_comando(
        self,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Adiciona uma resposta determinística à fila de chamadas de executar_comando."""
        self.fila_respostas_comandos.append(
            subprocess.CompletedProcess(
                args=[],
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        )

    def qual_executavel(self, nome: str) -> str | None:
        return self.executaveis.get(nome)

    def executar_comando(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        capturar_saida: bool = False,
        verificar: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        copia_cmd = list(cmd)
        self.comandos_executados.append(copia_cmd)
        if self.manipulador_comando is not None:
            res = self.manipulador_comando(copia_cmd, cwd, capturar_saida, verificar)
        elif self.fila_respostas_comandos:
            base = self.fila_respostas_comandos.pop(0)
            res = subprocess.CompletedProcess(
                args=copia_cmd,
                returncode=base.returncode,
                stdout=base.stdout,
                stderr=base.stderr,
            )
        else:
            res = subprocess.CompletedProcess(args=copia_cmd, returncode=0, stdout="", stderr="")

        if verificar and res.returncode != 0:
            raise subprocess.CalledProcessError(
                res.returncode, copia_cmd, output=res.stdout, stderr=res.stderr
            )
        return res

    def executar_pyinstaller(self, argumentos: list[str]) -> None:
        if not self.pyinstaller_disponivel:
            raise RuntimeError(
                "PyInstaller não está disponível neste ambiente. Ele é necessário para empacotamento em Windows e macOS."
            )
        self.chamadas_pyinstaller.append(list(argumentos))

    def executar_pytest(self, argumentos: list[str]) -> int:
        self.chamadas_pytest.append(list(argumentos))
        return self.codigo_pytest
