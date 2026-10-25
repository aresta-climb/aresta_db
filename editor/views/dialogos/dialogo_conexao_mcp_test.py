# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2026 Aresta Climb Contributors

from pathlib import Path

from PySide6.QtWidgets import QApplication

from editor.mcp.sessao import gravar_sessao_mcp
from editor.views.dialogos.dialogo_conexao_mcp import DialogoConexaoMcp


def test_dialogo_conexao_mcp_exibe_prompts_para_agentes_e_passo_a_passo_claude(
    qtbot,
) -> None:
    """
    Dado um servidor MCP ativo na porta 27380:
    - Para Antigravity, Codex e Cursor, deve orientar a copiar e colar o prompt no agente;
    - Para Claude Desktop, deve exibir as instruções passo a passo de configuração;
    - O botão Copiar embaixo deve copiar o conteúdo exibido para a área de transferência.
    """
    dialogo = DialogoConexaoMcp(porta=27380, servidor_ativo=True)
    qtbot.addWidget(dialogo)

    assert "27380" in dialogo.label_status.text()
    assert "Ativo" in dialogo.label_status.text()
    assert dialogo.edit_url.text() == "http://127.0.0.1:27380/mcp"

    clipboard = QApplication.clipboard()

    dialogo.btn_copiar_url.click()
    assert clipboard.text() == "http://127.0.0.1:27380/mcp"
    assert "URL" in dialogo.label_feedback.text()

    # 1. Google Antigravity: instrução de colar prompt no agente + botão Copiar
    dialogo.btn_antigravity.click()
    assert (
        "Copie e cole o prompt abaixo no seu agente para configurar o acesso ao Editor Aresta"
        in dialogo.label_instrucao.text()
    )
    dialogo.btn_copiar_snippet.click()
    texto_antigravity = clipboard.text()
    assert texto_antigravity == dialogo.edit_snippet.toPlainText()
    assert "mcp_config.json" in texto_antigravity
    assert "editor-aresta" in texto_antigravity
    assert '"serverUrl": "http://127.0.0.1:27380/mcp"' in texto_antigravity
    assert "Antigravity" in dialogo.label_feedback.text()

    # 2. OpenAI Codex: instrução de colar prompt no agente + botão Copiar
    dialogo.btn_codex.click()
    assert (
        "Copie e cole o prompt abaixo no seu agente para configurar o acesso ao Editor Aresta"
        in dialogo.label_instrucao.text()
    )
    dialogo.btn_copiar_snippet.click()
    texto_codex = clipboard.text()
    assert texto_codex == dialogo.edit_snippet.toPlainText()
    assert "config.toml" in texto_codex
    assert "editor-aresta" in texto_codex
    assert "http://127.0.0.1:27380/mcp" in texto_codex
    assert "Codex" in dialogo.label_feedback.text()

    # 3. Cursor: instrução de colar prompt no agente + botão Copiar
    dialogo.btn_cursor.click()
    assert (
        "Copie e cole o prompt abaixo no seu agente para configurar o acesso ao Editor Aresta"
        in dialogo.label_instrucao.text()
    )
    dialogo.btn_copiar_snippet.click()
    texto_cursor = clipboard.text()
    assert texto_cursor == dialogo.edit_snippet.toPlainText()
    assert "mcp.json" in texto_cursor
    assert "editor-aresta" in texto_cursor
    assert '"url": "http://127.0.0.1:27380/mcp"' in texto_cursor
    assert "Cursor" in dialogo.label_feedback.text()

    # 4. Claude Desktop: instruções passo a passo + snippet JSON + botão Copiar
    dialogo.btn_claude.click()
    assert "claude_desktop_config.json" in dialogo.label_instrucao.text()
    assert "1." in dialogo.label_instrucao.text()
    assert "2." in dialogo.label_instrucao.text()
    dialogo.btn_copiar_snippet.click()
    texto_claude = clipboard.text()
    assert texto_claude == dialogo.edit_snippet.toPlainText()
    assert "editor-aresta" in texto_claude
    assert "Claude Desktop" in dialogo.label_feedback.text()

    dialogo.btn_fechar.click()


def test_dialogo_conexao_mcp_descobre_sessao_ou_exibe_inativo(qtbot, tmp_path: Path) -> None:
    """Quando a porta não é informada explicitamente, o diálogo consulta a sessão persistida ou exibe status inativo."""
    dialogo_inativo = DialogoConexaoMcp(porta=None, servidor_ativo=False, dir_sessao=tmp_path)
    qtbot.addWidget(dialogo_inativo)
    assert "Inativo" in dialogo_inativo.label_status.text()
    assert "27378" in dialogo_inativo.edit_url.text()

    gravar_sessao_mcp(porta=27385, token="tok", diretorio_base=tmp_path)
    dialogo_sessao = DialogoConexaoMcp(porta=None, dir_sessao=tmp_path)
    qtbot.addWidget(dialogo_sessao)
    assert "Ativo" in dialogo_sessao.label_status.text()
    assert dialogo_sessao.edit_url.text() == "http://127.0.0.1:27385/mcp"
