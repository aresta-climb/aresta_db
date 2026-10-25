# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

import json
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from editor.core.configuracao_canal import obter_configuracao_canal
from editor.mcp.sessao import PORTA_MCP_PADRAO, ler_sessao_mcp

TEXTO_INSTRUCAO_PROMPT_AGENTE = (
    "Copie e cole o prompt abaixo no seu agente para configurar o acesso ao Editor Aresta:"
)

TEXTO_INSTRUCAO_CLAUDE_DESKTOP = (
    "Siga o passo a passo abaixo para configurar o Claude Desktop:\n"
    "1. No Claude Desktop, abra Configurações (Settings) > Desenvolvedor (Developer) > "
    "Editar Configuração (Edit Config) para abrir o arquivo claude_desktop_config.json.\n"
    '2. Copie a configuração abaixo, insira dentro de "mcpServers", salve o arquivo '
    "e reinicie o Claude Desktop:"
)


class DialogoConexaoMcp(QDialog):
    """
    Diálogo informativo para conectar agentes externos de IA (Antigravity, Codex,
    Claude Desktop e Cursor) ao servidor MCP integrado do Editor Aresta.
    """

    def __init__(
        self,
        porta: int | None = None,
        servidor_ativo: bool = True,
        dir_sessao: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if porta is None:
            sessao = ler_sessao_mcp(diretorio_base=dir_sessao)
            if sessao is not None:
                porta = sessao.porta
                servidor_ativo = True
            else:
                porta = PORTA_MCP_PADRAO
                servidor_ativo = False

        self.porta: int = porta
        self.servidor_ativo: bool = servidor_ativo
        self.url_sse: str = f"http://127.0.0.1:{self.porta}/mcp/sse"
        self.url_http: str = f"http://127.0.0.1:{self.porta}/mcp"
        self._agente_selecionado: str = "Google Antigravity"

        config_canal = obter_configuracao_canal()
        caminho_logo_janela = config_canal.obter_caminho_icone_aplicacao()
        self.setWindowIcon(QIcon(str(caminho_logo_janela)))
        self.setWindowTitle("Conectar Agente de IA (MCP)")
        self.setMinimumWidth(600)

        self._construir_interface()

    def _construir_interface(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        titulo = QLabel("Conectar Agente de IA (Model Context Protocol)")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #212529;")
        layout.addWidget(titulo)

        if self.servidor_ativo:
            texto_status = f"● Servidor MCP Ativo na porta {self.porta}"
            cor_status = "#198754"
        else:
            texto_status = f"○ Servidor MCP Inativo (porta padrão: {self.porta})"
            cor_status = "#6c757d"

        self.label_status = QLabel(texto_status)
        self.label_status.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {cor_status};")
        layout.addWidget(self.label_status)

        linha_url = QHBoxLayout()
        self.edit_url = QLineEdit(self.url_http)
        self.edit_url.setReadOnly(True)
        linha_url.addWidget(self.edit_url)

        self.btn_copiar_url = QPushButton("Copiar URL")
        self.btn_copiar_url.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar_url.clicked.connect(self._copiar_url)
        linha_url.addWidget(self.btn_copiar_url)
        layout.addLayout(linha_url)

        descricao = QLabel("Selecione o seu assistente de IA:")
        descricao.setStyleSheet("color: #495057; font-size: 13px; font-weight: bold;")
        layout.addWidget(descricao)

        linha_agentes = QHBoxLayout()
        self.btn_antigravity = QPushButton("Google Antigravity")
        self.btn_antigravity.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_antigravity.clicked.connect(self._selecionar_antigravity)
        linha_agentes.addWidget(self.btn_antigravity)

        self.btn_codex = QPushButton("OpenAI Codex")
        self.btn_codex.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_codex.clicked.connect(self._selecionar_codex)
        linha_agentes.addWidget(self.btn_codex)

        self.btn_claude = QPushButton("Claude Desktop")
        self.btn_claude.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_claude.clicked.connect(self._selecionar_claude)
        linha_agentes.addWidget(self.btn_claude)

        self.btn_cursor = QPushButton("Cursor")
        self.btn_cursor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cursor.clicked.connect(self._selecionar_cursor)
        linha_agentes.addWidget(self.btn_cursor)

        layout.addLayout(linha_agentes)

        self.label_instrucao = QLabel(TEXTO_INSTRUCAO_PROMPT_AGENTE)
        self.label_instrucao.setWordWrap(True)
        self.label_instrucao.setStyleSheet("color: #212529; font-size: 13px;")
        layout.addWidget(self.label_instrucao)

        self.edit_snippet = QPlainTextEdit()
        self.edit_snippet.setReadOnly(True)
        self.edit_snippet.setMinimumHeight(150)
        self.edit_snippet.setPlainText(self.gerar_snippet_antigravity())
        layout.addWidget(self.edit_snippet)

        linha_copiar_abaixo = QHBoxLayout()
        self.btn_copiar_snippet = QPushButton("Copiar")
        self.btn_copiar_snippet.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copiar_snippet.clicked.connect(self._copiar_snippet_atual)
        linha_copiar_abaixo.addWidget(self.btn_copiar_snippet)

        self.label_feedback = QLabel("")
        self.label_feedback.setStyleSheet("color: #0d6efd; font-size: 12px;")
        linha_copiar_abaixo.addWidget(self.label_feedback, stretch=1)
        layout.addLayout(linha_copiar_abaixo)

        rodape = QHBoxLayout()
        rodape.addStretch()
        self.btn_fechar = QPushButton("Fechar")
        self.btn_fechar.setDefault(True)
        self.btn_fechar.clicked.connect(self.accept)
        rodape.addWidget(self.btn_fechar)
        layout.addLayout(rodape)

    def _obter_comando_python(self) -> str:
        return Path(sys.executable).as_posix()

    def gerar_snippet_antigravity(self) -> str:
        caminho_cfg = (Path.home() / ".gemini" / "antigravity" / "mcp_config.json").as_posix()
        bloco = json.dumps(
            {
                "mcpServers": {
                    "editor-aresta": {
                        "serverUrl": self.url_http,
                    }
                }
            },
            indent=2,
            ensure_ascii=False,
        )
        return (
            "Configure o acesso ao servidor MCP do Editor Aresta adicionando a entrada "
            f"`editor-aresta` no seu arquivo `{caminho_cfg}` (preservando os demais "
            "servidores já existentes):\n\n"
            f"```json\n{bloco}\n```"
        )

    def gerar_snippet_codex(self) -> str:
        caminho_cfg = (Path.home() / ".codex" / "config.toml").as_posix()
        bloco_toml = f'[mcp_servers.editor-aresta]\nurl = "{self.url_http}"'
        return (
            "Configure o acesso ao servidor MCP do Editor Aresta adicionando a seção "
            f"`[mcp_servers.editor-aresta]` no seu arquivo `{caminho_cfg}` "
            "(preservando as demais configurações existentes):\n\n"
            f"```toml\n{bloco_toml}\n```"
        )

    def gerar_snippet_cursor(self) -> str:
        caminho_cfg = (Path.home() / ".cursor" / "mcp.json").as_posix()
        bloco = json.dumps(
            {
                "mcpServers": {
                    "editor-aresta": {
                        "url": self.url_http,
                    }
                }
            },
            indent=2,
            ensure_ascii=False,
        )
        return (
            "Configure o acesso ao servidor MCP do Editor Aresta adicionando a entrada "
            f"`editor-aresta` no arquivo `{caminho_cfg}` (ou `.cursor/mcp.json` do projeto, "
            "preservando os servidores existentes):\n\n"
            f"```json\n{bloco}\n```"
        )

    def gerar_snippet_claude(self) -> str:
        dados = {
            "mcpServers": {
                "editor-aresta": {
                    "command": self._obter_comando_python(),
                    "args": ["-m", "editor.mcp.bridge"],
                }
            }
        }
        return json.dumps(dados, indent=2, ensure_ascii=False)

    def _atualizar_painel_agente(self, instrucao: str, texto: str, nome_alvo: str) -> None:
        self._agente_selecionado = nome_alvo
        self.label_instrucao.setText(instrucao)
        self.edit_snippet.setPlainText(texto)
        self._copiar_snippet_atual()

    def _copiar_snippet_atual(self) -> None:
        texto = self.edit_snippet.toPlainText()
        QApplication.clipboard().setText(texto)
        self.label_feedback.setText(
            f"Copiado para {self._agente_selecionado} na área de transferência!"
        )

    def _copiar_url(self) -> None:
        QApplication.clipboard().setText(self.url_http)
        self.label_feedback.setText("URL MCP copiada para a área de transferência!")

    def _selecionar_antigravity(self) -> None:
        self._atualizar_painel_agente(
            TEXTO_INSTRUCAO_PROMPT_AGENTE,
            self.gerar_snippet_antigravity(),
            "Google Antigravity",
        )

    def _selecionar_codex(self) -> None:
        self._atualizar_painel_agente(
            TEXTO_INSTRUCAO_PROMPT_AGENTE,
            self.gerar_snippet_codex(),
            "OpenAI Codex",
        )

    def _selecionar_claude(self) -> None:
        self._atualizar_painel_agente(
            TEXTO_INSTRUCAO_CLAUDE_DESKTOP,
            self.gerar_snippet_claude(),
            "Claude Desktop",
        )

    def _selecionar_cursor(self) -> None:
        self._atualizar_painel_agente(
            TEXTO_INSTRUCAO_PROMPT_AGENTE,
            self.gerar_snippet_cursor(),
            "Cursor",
        )
