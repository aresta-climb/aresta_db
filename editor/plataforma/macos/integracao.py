# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

"""
Biblioteca utilitária para integração com o macOS (Cocoa / Apple Silicon).
Implementa o AdaptadorMacOS conforme o protocolo AdaptadorPlataforma.
"""

from pathlib import Path

from PySide6.QtCore import QStandardPaths

from editor.plataforma.contrato import (
    AdaptadorPlataforma,
    ResultadoAtualizacao,
    StatusAtualizacao,
)


class AdaptadorMacOS(AdaptadorPlataforma):
    """Adaptador de integração nativa com o sistema operacional macOS."""

    def configurar_ambiente_plataforma(self) -> None:
        """Configura variáveis de ambiente do subsistema gráfico antes da inicialização do Qt."""
        pass

    def configurar_presenca_barra_de_tarefas(self, identificador_janela: int) -> bool:
        """No macOS, a presença na Dock e alternador é gerenciada nativamente pelo sistema operacional."""
        return True

    def configurar_identidade_processo(self, identificador_app: str) -> bool:
        """Configura a identidade de aplicação no shell do sistema operacional."""
        try:
            from PySide6.QtGui import QGuiApplication

            QGuiApplication.setDesktopFileName(identificador_app)
            return True
        except Exception:
            return False

    def trazer_janela_para_frente(self, identificador_janela: int) -> bool:
        """Restaura e eleva a janela via APIs padrão do Qt."""
        try:
            from PySide6.QtWidgets import QApplication

            janela = QApplication.activeWindow()
            if janela is not None:
                janela.showNormal()
                janela.raise_()
                janela.activateWindow()
            return True
        except Exception:
            return False

    def obter_diretorio_dados_usuario(self) -> Path:
        """
        Retorna o diretório canônico de dados do usuário no macOS
        (~/Library/Application Support/EditorAresta).
        """
        caminho_appdata = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        if not caminho_appdata:
            return Path.home() / "Library" / "Application Support" / "EditorAresta"
        return Path(caminho_appdata)

    def __init__(
        self,
        versao_atual: str | None = None,
        url_feed: str | None = None,
    ) -> None:
        self._versao_atual = versao_atual
        self._url_feed = url_feed or "https://serving.arestaclimb.com/editor-macos/appcast.xml"

    def verificar_atualizacoes_disponiveis(self) -> ResultadoAtualizacao:
        """
        Consulta o feed XML de atualizações do macOS (Sparkle Framework) no Cloudflare R2.
        Compara a versão remota com a local e reporta ATUALIZACAO_OBRIGATORIA quando houver
        versão crítica pendente.
        """
        try:
            import re
            import urllib.request
            import xml.etree.ElementTree as ET

            from editor.core.version import VERSION

            versao_local = self._versao_atual or VERSION
            requisicao = urllib.request.Request(
                self._url_feed,
                headers={"User-Agent": f"EditorAresta/{versao_local}"},
            )
            with urllib.request.urlopen(requisicao, timeout=2.0) as resposta:
                conteudo_xml = resposta.read()

            raiz = ET.fromstring(conteudo_xml)
            canal = raiz.find("channel")
            if canal is None:
                return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

            item = canal.find("item")
            if item is None:
                return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

            enclosure = item.find("enclosure")
            if enclosure is None:
                return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

            versao_remota = None
            for chave, valor in enclosure.attrib.items():
                if chave.endswith("version"):
                    versao_remota = valor
                    break

            if not versao_remota:
                return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

            numeros_remoto = tuple(map(int, re.findall(r"\d+", versao_remota))) or (0,)
            numeros_local = tuple(map(int, re.findall(r"\d+", versao_local))) or (0,)

            if numeros_remoto > numeros_local:
                tem_critico = any(filho.tag.endswith("criticalUpdate") for filho in item)
                status = (
                    StatusAtualizacao.ATUALIZACAO_OBRIGATORIA
                    if tem_critico
                    else StatusAtualizacao.ATUALIZACAO_DISPONIVEL
                )
                return ResultadoAtualizacao(
                    status=status,
                    versao_disponivel=versao_remota,
                    mensagem="Nova versão do Editor Aresta disponível para macOS.",
                )

            return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)
        except Exception:
            return ResultadoAtualizacao(status=StatusAtualizacao.SEM_ATUALIZACAO)

    def solicitar_instalacao_atualizacao(
        self, resultado: ResultadoAtualizacao | None = None
    ) -> bool:
        """Dispara a instalação da atualização no macOS via Sparkle Framework."""
        try:
            from editor.plataforma.macos.sparkle import solicitar_verificacao_sparkle

            return bool(solicitar_verificacao_sparkle())
        except Exception:
            return False

    def obter_nome_icone_preferencial(self) -> str:
        """Retorna o nome do arquivo de ícone nativo prioritário para o macOS (.icns)."""
        return "logo.icns"

    def configurar_cofre_credenciais(self) -> bool:
        """Garante a seleção do Keychain no macOS para contornar limitações do PyInstaller."""
        try:
            import keyring
            from keyring.backends import fail

            backend_atual = keyring.get_keyring()
            if not isinstance(backend_atual, fail.Keyring):
                return True
        except Exception:
            return False

        try:
            from keyring.backends import macOS

            keyring.set_keyring(macOS.Keyring())  # type: ignore[no-untyped-call]
            return True
        except Exception:
            return False

    def normalizar_caminho_estendido(self, caminho: Path | str) -> str:
        """Em sistemas POSIX macOS, resolve e retorna o caminho absoluto canônico."""
        if not caminho:
            return ""
        return str(Path(caminho).resolve())
