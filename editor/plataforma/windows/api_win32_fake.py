# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca test-only de Fakes determinísticos para a fronteira Win32, Loja e Keyring do Windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from editor.plataforma.contrato import ResultadoAtualizacao, StatusAtualizacao


@dataclass
class ApiWin32Fake:
    """Dublê determinístico em memória da fronteira Win32 (user32, shell32, kernel32 e winreg)."""

    eh_windows: bool = True
    em_msix: bool = False
    falhar_operacao: bool = False
    hresult_aumid: int = 0
    estilos_janela: dict[tuple[int, int], int] = field(default_factory=dict)
    molduras_atualizadas: list[int] = field(default_factory=list)
    icones_hwnd: dict[int, str] = field(default_factory=dict)
    aumid_processo: str | None = None
    registro_aumid: dict[str, dict[str, str]] = field(default_factory=dict)
    janelas_focadas: list[int] = field(default_factory=list)

    def _verificar_falha(self) -> None:
        if self.falhar_operacao:
            raise OSError("Falha determinística simulada na fronteira Win32")

    def plataforma_eh_windows(self) -> bool:
        return self.eh_windows

    def esta_em_pacote_msix(self) -> bool:
        self._verificar_falha()
        if not self.eh_windows:
            return False
        return self.em_msix

    def definir_app_user_model_id(self, app_id: str) -> bool:
        self._verificar_falha()
        if self.hresult_aumid != 0:
            return False
        self.aumid_processo = app_id
        return True

    def registrar_metadados_aumid_usuario(
        self,
        app_id: str,
        nome_exibicao: str,
        caminho_icone: str,
    ) -> bool:
        self._verificar_falha()
        dados: dict[str, str] = {}
        if nome_exibicao:
            dados["DisplayName"] = nome_exibicao
        if caminho_icone:
            dados["IconUri"] = caminho_icone
        self.registro_aumid[app_id] = dados
        return True

    def obter_estilo_janela(self, identificador_janela: int, indice: int) -> int:
        self._verificar_falha()
        return self.estilos_janela.get((identificador_janela, indice), 0)

    def definir_estilo_janela(
        self, identificador_janela: int, indice: int, novo_estilo: int
    ) -> None:
        self._verificar_falha()
        self.estilos_janela[(identificador_janela, indice)] = novo_estilo

    def atualizar_moldura_janela(self, identificador_janela: int) -> None:
        self._verificar_falha()
        self.molduras_atualizadas.append(identificador_janela)

    def aplicar_icone_hwnd(self, identificador_janela: int, caminho_icone: str) -> bool:
        self._verificar_falha()
        if not caminho_icone:
            return False
        self.icones_hwnd[identificador_janela] = caminho_icone
        return True

    def restaurar_e_focar_janela(self, identificador_janela: int) -> None:
        self._verificar_falha()
        self.janelas_focadas.append(identificador_janela)


@dataclass
class ProvedorKeyringWindowsFake:
    """Dublê determinístico em memória para consulta e instalação do WinVaultKeyring."""

    backend_inicial_operacional: bool = True
    falhar_consulta: bool = False
    falhar_instalacao: bool = False
    backends_instalados: list[str] = field(default_factory=list)

    def backend_atual_eh_operacional(self) -> bool:
        if self.falhar_consulta:
            raise RuntimeError("Falha determinística ao consultar keyring")
        return self.backend_inicial_operacional

    def instalar_win_vault_keyring(self) -> Any:
        if self.falhar_instalacao:
            raise RuntimeError("Falha determinística ao instalar WinVaultKeyring")
        self.backends_instalados.append("WinVaultKeyring")
        self.backend_inicial_operacional = True
        return "WinVaultKeyring"


@dataclass
class ServicoLojaWindowsFake:
    """Dublê determinístico em memória para `ServicoLoja` da Microsoft Store."""

    resultado: ResultadoAtualizacao = field(
        default_factory=lambda: ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)
    )
    instalacoes: list[ResultadoAtualizacao | None] = field(default_factory=list)

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        return self.resultado

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        self.instalacoes.append(resultado)
        return True
